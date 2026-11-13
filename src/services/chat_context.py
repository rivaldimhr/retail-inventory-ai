"""Inventory context sent to the LLM together with the user's question."""


def _risky(p: dict) -> bool:
    return any(p["risk_flags"].values()) or p.get("recommended_order_qty", 0) > 0


def _category_summary(preds):
    cats = {}
    for p in preds:
        c = cats.setdefault(p["category"], {"category": p["category"], "products": 0, "need_reorder": 0,
                                            "out_of_stock": 0, "overstock": 0, "lost_revenue_30d": 0.0})
        c["products"] += 1
        c["need_reorder"] += int(p.get("recommended_order_qty", 0) > 0)
        c["out_of_stock"] += int(p["risk_flags"].get("out_of_stock", False))
        c["overstock"] += int(p["risk_flags"].get("overstock_risk", False))
        c["lost_revenue_30d"] = round(c["lost_revenue_30d"] + p.get("lost_revenue_30d", 0), 2)
    return sorted(cats.values(), key=lambda c: -c["lost_revenue_30d"])


def _pairs_for(products, mba):
    rules = (mba or {}).get("rules", [])
    out = []
    for p in products:
        name = p["product_name"].lower()
        for r in rules:
            a, b = r["antecedents"][0], r["consequents"][0]
            if name in (a.lower(), b.lower()):
                out.append({"product": p["product_name"], "bought_with": b if a.lower() == name else a,
                            "confidence": r["confidence"], "lift": r["lift"]})
    return out[:6]


def build_context(message: str, forecast: dict, mba: dict = None, metrics: dict = None) -> dict:
    """Summary of the whole inventory + the most urgent products + any product named in the question."""
    preds = forecast.get("predictions", [])
    flags = lambda k: [p for p in preds if p["risk_flags"].get(k)]  # noqa: E731
    urgent = sorted([p for p in preds if _risky(p)],
                    key=lambda p: (not p["risk_flags"]["stockout_risk"], -p["revenue_at_risk"], p["stock_coverage_days"]))
    text = message.lower()
    words = set(text.replace(",", " ").split())
    mentioned = [p for p in preds if p["product_id"].lower() in words or p["product_name"].lower() in text]
    if not mentioned:  # partial names, e.g. "jumbo bag doily"
        def hits(p):
            name_words = [w for w in p["product_name"].lower().split() if len(w) > 3]
            return sum(w in words for w in name_words)
        best = max((hits(p) for p in preds), default=0)
        if best >= 2:
            mentioned = [p for p in preds if hits(p) == best]
    mentioned = mentioned[:3]
    return {
        "data_as_of": forecast.get("data_as_of"),
        "currency": forecast.get("currency", "GBP"),
        "total_count": len(preds),
        "stockout_count": len(flags("stockout_risk")),
        "overstock_count": len(flags("overstock_risk")),
        "deadstock_count": len(flags("deadstock_risk")),
        "lost_sales_count": len(flags("missed_revenue_flag")),
        "reorder_count": sum(1 for p in preds if p.get("recommended_order_qty", 0) > 0),
        "revenue_at_risk_total": round(sum(p.get("revenue_at_risk", 0) for p in preds), 2),
        "out_of_stock_count": len(flags("out_of_stock")),
        "top_risks": urgent[:8],
        "mentioned_products": mentioned,
        "top_sellers_next_7d": sorted(preds, key=lambda p: -p["demand_signal"]["forecast_7d"])[:5],
        "categories": _category_summary(preds),
        "top_basket_pairs": [{"a": r["antecedents"][0], "b": r["consequents"][0], "confidence": r["confidence"],
                              "lift": r["lift"]} for r in (mba or {}).get("rules", [])[:5]],
        "pairs_for_mentioned": _pairs_for(mentioned, mba),
        "model_accuracy": None if not metrics else {
            "test_period": metrics.get("test_period"),
            "wape": metrics["metrics"]["model"]["wape"],
            "mae_units_per_product_week": metrics["metrics"]["model"]["mae"],
            "improvement_vs_best_baseline": metrics.get("mae_improvement_vs_best_baseline"),
        },
    }
