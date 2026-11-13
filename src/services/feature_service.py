"""Features for the 7-day demand forecast.

Every feature for day t uses only information available at the end of day t,
and the target is the total demand of the NEXT 7 days (t+1 .. t+7). No future data leaks in.
"""
import numpy as np
import pandas as pd

from src.config.config import config

FEATURES = [
    "units_today", "mean_7", "mean_14", "mean_28", "mean_56", "std_28",
    "nonzero_days_28", "days_since_last_sale", "trend_ratio",
    "price", "price_ratio_28", "product_mean_to_date",
    "month_next", "days_to_christmas", "holidays_next_7", "category_code",
    "orders_mean_7", "orders_mean_28", "median_28", "day_of_week",
    "last_year_next_7", "last_year_last_7", "last_year_growth",
]
TARGET = "target_next_7"


def _uk_holidays(years):
    try:
        import holidays
        return set(holidays.UK(years=years).keys())
    except Exception:  # library not installed: run without holiday feature
        return set()


def add_features(daily: pd.DataFrame) -> pd.DataFrame:
    df = daily.sort_values(["stock_code", "date"]).copy()
    g = df.groupby("stock_code", sort=False)["units_sold"]

    df["units_today"] = df["units_sold"]
    for w in (7, 14, 28, 56):
        df[f"mean_{w}"] = g.transform(lambda s, w=w: s.rolling(w, min_periods=1).mean())
    df["std_28"] = g.transform(lambda s: s.rolling(28, min_periods=2).std()).fillna(0)
    df["nonzero_days_28"] = g.transform(lambda s: (s > 0).astype(float).rolling(28, min_periods=1).sum())
    df["product_mean_to_date"] = g.transform(lambda s: s.expanding().mean())
    df["trend_ratio"] = (df["mean_7"] + 0.1) / (df["mean_28"] + 0.1)

    # Days since the product last sold (0 = sold today).
    sold = df["units_sold"] > 0
    last_sale = df["date"].where(sold).groupby(df["stock_code"]).ffill()
    df["days_since_last_sale"] = (df["date"] - last_sale).dt.days.fillna(999).clip(upper=999)

    price_mean = df.groupby("stock_code", sort=False)["price"].transform(lambda s: s.rolling(28, min_periods=1).mean())
    df["price_ratio_28"] = (df["price"] / price_mean).replace([np.inf, -np.inf], 1).fillna(1)

    # Calendar features describe the coming week, which is known in advance.
    next_day = df["date"] + pd.Timedelta(days=1)
    df["month_next"] = next_day.dt.month
    christmas = pd.to_datetime(df["date"].dt.year.astype(str) + "-12-25")
    days_to = (christmas - df["date"]).dt.days
    df["days_to_christmas"] = days_to.where(days_to >= 0, days_to + 365).clip(upper=180)

    hol = _uk_holidays(sorted(df["date"].dt.year.unique().tolist() + [int(df["date"].dt.year.max()) + 1]))
    if hol:
        hol_days = pd.Series(1, index=pd.to_datetime(sorted(hol)))
        all_days = pd.date_range(df["date"].min(), df["date"].max() + pd.Timedelta(days=8))
        flags = hol_days.reindex(all_days, fill_value=0)
        next7 = flags[::-1].rolling(7, min_periods=1).sum()[::-1].shift(-1).fillna(0)
        df["holidays_next_7"] = df["date"].map(next7).fillna(0)
    else:
        df["holidays_next_7"] = 0.0

    df["category_code"] = df["category"].astype("category").cat.codes
    df["day_of_week"] = df["date"].dt.day_of_week

    # Number of orders (invoices) is steadier than units, because one wholesale order can be huge.
    orders = df.groupby("stock_code", sort=False)["invoices"]
    df["orders_mean_7"] = orders.transform(lambda s: s.rolling(7, min_periods=1).mean())
    df["orders_mean_28"] = orders.transform(lambda s: s.rolling(28, min_periods=1).mean())
    df["median_28"] = g.transform(lambda s: s.rolling(28, min_periods=1).median())

    # Target: total demand over the next 7 days (NaN where the future is not observed).
    rev = df.groupby("stock_code", sort=False)["units_sold"].transform(
        lambda s: s[::-1].rolling(config.HORIZON_DAYS, min_periods=config.HORIZON_DAYS).sum()[::-1].shift(-1)
    )
    df[TARGET] = rev

    # Same week one year earlier (364 days = 52 weeks, so weekdays line up). Entirely in the past.
    by_code = df.groupby("stock_code", sort=False)
    last_7 = g.transform(lambda s: s.rolling(7, min_periods=1).sum())
    df["last_year_next_7"] = by_code[TARGET].shift(364)
    df["last_year_last_7"] = last_7.groupby(df["stock_code"]).shift(364)
    df["last_year_growth"] = (df["last_year_next_7"] + 1) / (df["last_year_last_7"] + 1)
    return df
