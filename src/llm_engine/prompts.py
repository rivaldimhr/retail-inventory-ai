CHAT_SYSTEM_PROMPT = """You are an inventory analyst assistant for an online retail shop that sells giftware and homeware.
You receive a snapshot of the shop's inventory: 7-day demand forecasts, current stock, recommended order quantities and risk flags.

Rules:
- Answer only from the data provided. If the data does not contain the answer, say so.
- Be brief (2-5 sentences) and practical: say what to do, for which product, and how many units.
- Quote specific numbers (units, days of coverage, money in the given currency).
- Stockout risk means stock plus open orders will not last until the next delivery arrives.
- Reply in the same language as the user (Indonesian or English).
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
        f"- Stockout risk: {ctx.get('stockout_count', 0)}, overstock: {ctx.get('overstock_count', 0)}, "
        f"deadstock: {ctx.get('deadstock_count', 0)}, had lost sales (30 days): {ctx.get('lost_sales_count', 0)}",
        f"- Total revenue at risk before next deliveries: {cur} {ctx.get('revenue_at_risk_total', 'N/A')}",
        "",
        "Most urgent products:",
    ]
    lines += [_product_line(p, cur) for p in ctx.get("top_risks", [])] or ["- none"]
    if ctx.get("mentioned_products"):
        lines += ["", "Products mentioned in the question:"]
        lines += [_product_line(p, cur) for p in ctx["mentioned_products"]]
    return "\n".join(lines) + f"\n\nUser question: {message}"
