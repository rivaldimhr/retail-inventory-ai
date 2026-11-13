CHAT_SYSTEM_PROMPT = """You are an inventory analyst assistant for an online retail shop that sells giftware and homeware.
You receive a snapshot of the shop's inventory: 7-day demand forecasts, current stock, recommended order quantities and risk flags.

Rules:
- Answer only from the data provided. If the data does not contain the answer, say so.
- Be brief (2-5 sentences) and practical: say what to do, for which product, and how many units.
- Quote specific numbers (units, days of coverage, money in the given currency).
- Stockout risk means stock plus open orders will not last until the next delivery arrives.
- Reply in the same language as the user (Indonesian or English).
- You can also answer about categories, best sellers, products bought together (market basket) and forecast accuracy
  when that data is provided. Accuracy = 100% - WAPE.
- Politely decline questions unrelated to inventory, sales or the shop."""


def _product_line(p: dict, currency: str) -> str:
    d = p.get("demand_signal", {})
    flags = [k.replace("_", " ") for k, v in p.get("risk_flags", {}).items() if v] or ["no risk"]
    return (
        f"- {p.get('product_name')} [{p.get('product_id')}, {p.get('category')}]: "
        f"stock {p.get('current_stock')} (+{p.get('on_order', 0)} on order), "
        f"forecast next 7 days {d.get('forecast_7d')} units, coverage {p.get('stock_coverage_days')} days, "
        f"lead time {p.get('lead_time_days')} days, recommended order {p.get('recommended_order_qty', 0)} units, "
        f"revenue at risk {currency} {p.get('revenue_at_risk', 0)}, "
        f"lost sales last 30 days {d.get('lost_sales_30d', 0)} units, trend {p.get('trend_direction')}, "
        f"flags: {', '.join(flags)}"
    )


def build_chat_prompt(message: str, ctx: dict = None) -> str:
    if not ctx:
        return f"(No inventory data is available yet.)\n\nUser question: {message}"
    cur = ctx.get("currency", "GBP")
    lines = [
        f"Inventory snapshot (data as of {ctx.get('data_as_of', 'unknown')}):",
        f"- Products monitored: {ctx.get('total_count', 'N/A')}",
        f"- Need reordering now: {ctx.get('reorder_count', 'N/A')}",
        f"- Out of stock now: {ctx.get('out_of_stock_count', 0)}, stockout risk: {ctx.get('stockout_count', 0)}, overstock: {ctx.get('overstock_count', 0)}, "
        f"deadstock: {ctx.get('deadstock_count', 0)}, had lost sales (30 days): {ctx.get('lost_sales_count', 0)}",
        f"- Total revenue at risk before next deliveries: {cur} {ctx.get('revenue_at_risk_total', 'N/A')}",
        "",
        "Most urgent products:",
    ]
    lines += [_product_line(p, cur) for p in ctx.get("top_risks", [])] or ["- none"]
    if ctx.get("top_sellers_next_7d"):
        lines += ["", "Best sellers expected in the next 7 days:"]
        lines += [_product_line(p, cur) for p in ctx["top_sellers_next_7d"]]
    if ctx.get("categories"):
        lines += ["", "Categories (sorted by lost revenue in the last 30 days):"]
        lines += [f"- {c['category']}: {c['products']} products, {c['need_reorder']} need reordering, "
                  f"{c['out_of_stock']} out of stock, {c['overstock']} overstock, lost {cur} {c['lost_revenue_30d']}"
                  for c in ctx["categories"]]
    if ctx.get("top_basket_pairs"):
        lines += ["", "Strongest product pairs bought together:"]
        lines += [f"- {r['a']} -> {r['b']} (confidence {r['confidence']:.0%}, lift {r['lift']:.1f})" for r in ctx["top_basket_pairs"]]
    if ctx.get("model_accuracy"):
        a = ctx["model_accuracy"]
        lines += ["", f"Forecast accuracy (test {a['test_period']}): {1 - a['wape']:.1%} accuracy, "
                      f"MAE {a['mae_units_per_product_week']} units per product per week, "
                      f"{a['improvement_vs_best_baseline']:.1%} better than the best simple baseline."]
    if ctx.get("mentioned_products"):
        lines += ["", "Products mentioned in the question:"]
        lines += [_product_line(p, cur) for p in ctx["mentioned_products"]]
    if ctx.get("pairs_for_mentioned"):
        lines += ["", "Often bought together with the mentioned products:"]
        lines += [f"- {r['product']} + {r['bought_with']} (confidence {r['confidence']:.0%}, lift {r['lift']:.1f})"
                  for r in ctx["pairs_for_mentioned"]]
    return "\n".join(lines) + f"\n\nUser question: {message}"
