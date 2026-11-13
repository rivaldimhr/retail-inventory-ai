"""Turn the forecast and simulated stock into decisions: risk flags, order quantity, money at risk."""
import math
from datetime import datetime

import pandas as pd

from src.config.config import config


def _trend(recent: float, previous: float) -> str:
    if recent + previous < 1:            # too little volume to call a trend
        return "STABLE"
    ratio = (recent + 0.5) / (previous + 0.5)
    if ratio >= 1.25:
        return "INCREASING"
    if ratio <= 0.8:
        return "DECREASING"
    return "STABLE"


def build_snapshot(simulated: pd.DataFrame, latest: pd.DataFrame) -> dict:
    """simulated: daily table with stock columns. latest: one row per product with forecast_7d."""
    z = config.SERVICE_LEVEL_Z
    as_of = simulated["date"].max()
    hist = simulated.sort_values("date").groupby("stock_code", sort=False)

    predictions = []
    for _, row in latest.iterrows():
        h = hist.get_group(row["stock_code"])
        units = h["units_sold"].to_numpy()
        lost = h["lost_sales"].to_numpy()
        price = float(row["price"]) if pd.notna(row["price"]) else 0.0
        lt = int(row["lead_time_days"])
        stock = float(row["stock_qty"])
        # The simulated policy may already have placed an order today. Leave today's decision
        # to the manager: the recommendation below replaces that automatic order.
        on_order = float(row["on_order"]) - float(row.get("ordered", 0) or 0)
        position = stock + on_order

        forecast_7d = float(row["forecast_7d"])
        daily_fc = forecast_7d / config.HORIZON_DAYS
        std_d = float(row["std_28"])
        safety = z * std_d * math.sqrt(lt)
        reorder_point = daily_fc * lt + safety
        coverage = stock / daily_fc if daily_fc > 0.01 else 999.0

        order_qty = 0
        if position <= reorder_point and daily_fc > 0:
            order_qty = max(0, math.ceil(daily_fc * (lt + config.REVIEW_DAYS) + safety - position))

        shortfall = max(0.0, daily_fc * lt - position)
        lost_30 = float(lost[-30:].sum())
        days_since = int(row["days_since_last_sale"])
        trend = _trend(units[-14:].mean(), units[-28:-14].mean() if len(units) >= 28 else units.mean())

        deadstock = days_since >= config.DEADSTOCK_NO_SALE_DAYS and stock > 0
        flags = {
            # Nothing on the shelf right now (even if a delivery is on its way): sales are being lost today.
            "out_of_stock": bool(stock <= 0 and daily_fc > 0),
            "stockout_risk": bool(daily_fc > 0 and position < daily_fc * lt),
            "overstock_risk": bool(not deadstock and coverage > config.OVERSTOCK_DAYS and stock > 0),
            "deadstock_risk": bool(deadstock),
            "promo_opportunity": bool(not deadstock and trend == "DECREASING" and coverage > 30),
            "missed_revenue_flag": bool(lost_30 > 0),
        }

        predictions.append({
            "product_id": row["stock_code"],
            "product_name": str(row["description"]).title(),
            "category": row["category"],
            "unit_price": round(price, 2),
            "current_stock": int(stock),
            "on_order": int(on_order),
            "lead_time_days": lt,
            "safety_stock": int(math.ceil(safety)),
            "reorder_point": int(math.ceil(reorder_point)),
            "stock_coverage_days": round(min(coverage, 999.0), 1),
            "trend_direction": trend,
            "demand_signal": {
                "forecast_7d": round(forecast_7d, 1),
                "avg_daily_demand_forecast": round(daily_fc, 2),
                "actual_last_7d": int(units[-7:].sum()),
                "avg_sales_30d_actual": round(float(units[-30:].mean()), 2),
                "lost_sales_30d": int(lost_30),
                "unmet_demand_flag": bool(lost_30 > 0),
            },
            "recommended_order_qty": int(order_qty),
            "revenue_at_risk": round(shortfall * price, 2),
            "lost_revenue_30d": round(lost_30 * price, 2),
            "days_since_last_sale": days_since,
            "risk_flags": flags,
        })

    predictions.sort(key=lambda p: (not p["risk_flags"]["stockout_risk"], not p["risk_flags"]["out_of_stock"],
                                    -p["revenue_at_risk"], -p["demand_signal"]["forecast_7d"]))
    return {
        "generated_at": datetime.now().isoformat(),
        "data_as_of": str(as_of.date()),
        "currency": "GBP",
        "horizon_days": config.HORIZON_DAYS,
        "predictions": predictions,
    }
