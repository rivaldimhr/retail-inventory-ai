"""Inventory simulation.

Online Retail II contains sales, not stock levels, so stock is simulated with a standard
reorder-point policy that a real store could run:

* each product gets a supplier lead time (3, 5, 7 or 10 days, fixed per product);
* reorder point  = average daily demand x lead time + safety stock;
* safety stock   = z x std of daily demand x sqrt(lead time)   (z = 1.65 -> ~95% service level);
* when stock + open orders fall to the reorder point, order enough to cover
  lead time + review period (14 days) + safety stock.

Averages use only the previous 28 days, so the policy never "sees the future".
Demand that cannot be served because stock is empty is recorded as lost sales.
"""
import math
import zlib

import numpy as np
import pandas as pd

from src.config.config import config

WINDOW = 28


def lead_time_for(stock_code: str) -> int:
    """Deterministic lead time per product (stable across runs)."""
    options = config.LEAD_TIME_OPTIONS
    return int(options[zlib.crc32(stock_code.encode()) % len(options)])


def simulate_product(units: np.ndarray, lead_time: int, z: float = None, review_days: int = None):
    """Simulate one product. Returns arrays: stock (end of day), on_order, lost, received, ordered."""
    z = config.SERVICE_LEVEL_Z if z is None else z
    review_days = config.REVIEW_DAYS if review_days is None else review_days
    n = len(units)
    stock_out = np.zeros(n)
    on_order_out = np.zeros(n)
    lost = np.zeros(n)
    received = np.zeros(n)
    ordered = np.zeros(n)

    warm = units[:WINDOW]
    mean0 = warm.mean() if len(warm) else 0.0
    std0 = warm.std() if len(warm) else 0.0
    stock = math.ceil(mean0 * (lead_time + review_days) + z * std0 * math.sqrt(lead_time))
    pipeline = []  # list of [arrival_day, qty]

    for t in range(n):
        arrived = sum(q for d, q in pipeline if d <= t)
        pipeline = [[d, q] for d, q in pipeline if d > t]
        stock += arrived
        received[t] = arrived

        demand = units[t]
        sold = min(stock, demand)
        lost[t] = demand - sold
        stock -= sold

        lo = max(0, t - WINDOW + 1)
        hist = units[lo:t + 1]
        mean_d = hist.mean()
        std_d = hist.std()
        safety = z * std_d * math.sqrt(lead_time)
        reorder_point = mean_d * lead_time + safety
        open_qty = sum(q for _, q in pipeline)
        if mean_d > 0 and stock + open_qty <= reorder_point:
            target = mean_d * (lead_time + review_days) + safety
            qty = math.ceil(target - stock - open_qty)
            if qty > 0:
                pipeline.append([t + lead_time, qty])
                ordered[t] = qty
                open_qty += qty

        stock_out[t] = stock
        on_order_out[t] = open_qty

    return stock_out, on_order_out, lost, received, ordered


def simulate_stock(daily: pd.DataFrame) -> pd.DataFrame:
    """Add stock_qty, on_order, lost_sales, received, ordered and lead_time_days to the daily table."""
    parts = []
    for code, g in daily.groupby("stock_code", sort=False):
        g = g.sort_values("date").copy()
        lt = lead_time_for(code)
        stock, on_order, lost, received, ordered = simulate_product(g["units_sold"].to_numpy(dtype=float), lt)
        g["lead_time_days"] = lt
        g["stock_qty"] = stock
        g["on_order"] = on_order
        g["lost_sales"] = lost
        g["received"] = received
        g["ordered"] = ordered
        parts.append(g)
    return pd.concat(parts, ignore_index=True)
