"""Inventory context sent to the LLM together with the user's question."""


def _risky(p: dict) -> bool:
    return any(p["risk_flags"].values()) or p.get("recommended_order_qty", 0) > 0


def build_context(message: str, forecast: dict) -> dict:
    """Summary of the whole inventory + the most urgent products + any product named in the question."""
    preds = forecast.get("predictions", [])
    flags = lambda k: [p for p in preds if p["risk_flags"].get(k)]  # noqa: E731
    urgent = sorted([p for p in preds if _risky(p)],
                    key=lambda p: (not p["risk_flags"]["stockout_risk"], -p["revenue_at_risk"], p["stock_coverage_days"]))
    text = message.lower()
    mentioned = [p for p in preds if p["product_id"].lower() in text or p["product_name"].lower() in text][:3]
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
        "top_risks": urgent[:8],
        "mentioned_products": mentioned,
    }
