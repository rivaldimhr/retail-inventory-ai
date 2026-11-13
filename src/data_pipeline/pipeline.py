"""Turn clean transactions into a complete daily demand table per product."""
import re

import numpy as np
import pandas as pd

# Keyword rules for product categories (Online Retail II has no category column).
# Order matters: the first matching rule wins.
CATEGORY_RULES = [
    ("Christmas & seasonal", ("CHRISTMAS", "XMAS", "ADVENT", "EASTER", "SNOWFLAKE", "REINDEER", "SANTA")),
    ("Baking & party", ("CAKE", "BAKING", "CUPCAKE", "PARTY", "BUNTING", "NAPKIN", "BALLOON")),
    ("Bags & storage", ("BAG", "TOTE", "STORAGE", "BOX", "TIN", "BASKET", "HAMPER")),
    ("Kitchen & dining", ("MUG", "CUP", "TEA", "PLATE", "BOWL", "JAR", "BOTTLE", "SPOON", "APRON", "LUNCH", "TRAY", "GLASS")),
    ("Candles & lighting", ("CANDLE", "T-LIGHT", "TLIGHT", "LIGHT", "LANTERN", "LAMP")),
    ("Stationery & gift wrap", ("CARD", "WRAP", "PAPER", "NOTEBOOK", "PEN", "PENCIL", "STICKER", "TAPE", "ENVELOPE", "CHALK")),
    ("Toys & games", ("TOY", "GAME", "DOLL", "PUZZLE", "SKITTLES", "DOMINOES", "SPACEBOY")),
    ("Home decor", ("HEART", "SIGN", "FRAME", "DECORATION", "ORNAMENT", "HANGING", "WREATH", "CUSHION", "CLOCK", "MIRROR", "DOORSTOP", "HOOK", "BUNNY")),
    ("Garden", ("GARDEN", "PLANT", "FLOWER POT", "WATERING", "BIRD")),
    ("Fashion & accessories", ("NECKLACE", "BRACELET", "EARRINGS", "RING", "UMBRELLA", "PURSE", "HAIR", "SCARF")),
]


_CATEGORY_PATTERNS = [
    (name, re.compile(r"(?<![A-Z])(?:" + "|".join(re.escape(k) for k in words) + ")"))
    for name, words in CATEGORY_RULES
]


def categorize(description: str) -> str:
    """Keywords must start a word, so 'TIN' matches 'TIN BOX' but not 'PAINTING'."""
    text = str(description).upper()
    for category, pattern in _CATEGORY_PATTERNS:
        if pattern.search(text):
            return category
    return "Other"


def select_top_products(tx: pd.DataFrame, top_n: int) -> list:
    """Most frequently ordered products (by number of distinct invoices)."""
    counts = tx.groupby("stock_code")["invoice"].nunique().sort_values(ascending=False)
    return counts.head(top_n).index.tolist()


def build_daily_demand(tx: pd.DataFrame, products: list) -> pd.DataFrame:
    """Daily units sold per product, with every calendar day present (missing days = 0).

    Very large one-off wholesale orders are capped at each product's 99th percentile of
    non-zero daily demand, so a single bulk order does not dominate the model.
    """
    tx = tx[tx["stock_code"].isin(products)]
    daily = (
        tx.groupby(["stock_code", "date"])
        .agg(units_sold=("quantity", "sum"), price=("price", "median"), invoices=("invoice", "nunique"))
        .reset_index()
    )
    caps = daily.groupby("stock_code")["units_sold"].quantile(0.99)
    daily["units_raw"] = daily["units_sold"]
    daily["units_sold"] = np.minimum(daily["units_sold"], daily["stock_code"].map(caps)).round()

    dates = pd.date_range(tx["date"].min(), tx["date"].max(), freq="D")
    full = pd.MultiIndex.from_product([products, dates], names=["stock_code", "date"])
    daily = daily.set_index(["stock_code", "date"]).reindex(full).reset_index()
    daily[["units_sold", "units_raw", "invoices"]] = daily[["units_sold", "units_raw", "invoices"]].fillna(0)
    # Carry the last known price forward (then backward for days before the first sale).
    daily["price"] = daily.groupby("stock_code")["price"].transform(lambda s: s.ffill().bfill())

    meta = (
        tx.drop_duplicates("stock_code")[["stock_code", "description"]]
        .assign(category=lambda d: d["description"].map(categorize))
    )
    daily = daily.merge(meta, on="stock_code", how="left")
    return daily.sort_values(["stock_code", "date"]).reset_index(drop=True)
