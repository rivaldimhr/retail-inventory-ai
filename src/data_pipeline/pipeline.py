"""Turn clean transactions into a complete daily demand table per product."""
import re

import numpy as np
import pandas as pd

# Keyword rules for product categories (Online Retail II has no category column).
# Order matters: the first matching rule wins.
CATEGORY_RULES = [
    ("Christmas & seasonal", ("CHRISTMAS", "XMAS", "ADVENT", "EASTER", "SNOWFLAKE", "REINDEER", "SANTA")),
    ("Baking & party", ("CAKE", "BAKING", "CUPCAKE", "COOKIE", "PARTY", "BUNTING", "NAPKIN", "BALLOON")),
    ("Bags & storage", ("BAG", "TOTE", "STORAGE", "BOX", "TIN", "BASKET", "HAMPER", "SHOPPER", "PURSE", "WASHBAG", "CASE")),
    ("Accessories & warmers", ("NECKLACE", "BRACELET", "EARRINGS", "RING", "UMBRELLA", "HAIR", "SCARF", "HAND WARMER",
                               "HOT WATER BOTTLE", "SLIPPER", "MITTEN", "PARASOL", "SILK FAN", "KEY FOB")),
    ("Kitchen & dining", ("MUG", "CUP", "TEA", "PLATE", "BOWL", "JAR", "BOTTLE", "SPOON", "APRON", "LUNCH", "TRAY", "GLASS",
                          "JELLY", "JAM ", "POPCORN", "MOULD", "CUTLERY", "COASTER", "TOAST", "EGG ", "RECIPE", "KITCHEN", "CHOPSTICK", "JUG", "PEG", "GLOVE", "WASHING UP", "DOILIES")),
    ("Candles & lighting", ("CANDLE", "T-LIGHT", "TLIGHT", "LIGHT", "LANTERN", "LAMP")),
    ("Stationery & gift wrap", ("CARD", "WRAP", "PAPER", "NOTEBOOK", "PEN", "PENCIL", "STICKER", "TAPE", "ENVELOPE", "CHALK",
                                "RIBBON", "GIFT", "TISSUE", "TAG", "STAMP", "ERASER", "RULER", "JOURNAL")),
    ("Toys & games", ("TOY", "GAME", "DOLL", "PUZZLE", "SKITTLES", "DOMINOES", "SPACEBOY", "CRAYON", "CLAY", "KNITTING",
                      "SKIPPING", "GLIDER", "COLOURING", "PAINT SET", "BALL", "SOLDIER", "TEDDY", "PLAYHOUSE", "MAGIC", "BINGO", "FELTCRAFT", "SPINNING TOP", "SNAKES", "SEWING")),
    ("Home decor", ("HEART", "SIGN", "FRAME", "DECORATION", "ORNAMENT", "HANGING", "WREATH", "CUSHION", "CLOCK", "MIRROR", "DOORSTOP", "HOOK", "BUNNY",
                    "BLACKBOARD", "BLACK BOARD", "CHALKBOARD", "VASE", "DOORMAT", "BUNTING", "GARLAND", "PICTURE", "TRINKET", "DRAWER", "KNOB", "PLAQUE", "BIRD",
                    "CABINET", "CHEST", "COAT RACK", "PAINTING", "BUILDING BLOCK", "MEMO BOARD", "STAR")),
    ("Garden", ("GARDEN", "PLANT", "FLOWER POT", "WATERING", "BIRD")),
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


def drop_incomplete_last_day(tx: pd.DataFrame, threshold: float = 0.5) -> pd.DataFrame:
    """The export can stop in the middle of a day (Online Retail II ends at noon on 2011-12-09).
    If the last day has far fewer invoices than a normal trading day, leave it out."""
    per_day = tx.groupby("date")["invoice"].nunique()
    if len(per_day) < 8:
        return tx
    typical = per_day.iloc[-29:-1].median()
    if per_day.iloc[-1] < threshold * typical:
        return tx[tx["date"] < per_day.index[-1]]
    return tx


def build_daily_demand(tx: pd.DataFrame, products: list) -> pd.DataFrame:
    """Daily units sold per product, with every calendar day present (missing days = 0).

    Very large one-off wholesale orders are capped at each product's 99th percentile of
    non-zero daily demand, so a single bulk order does not dominate the model.
    """
    tx = drop_incomplete_last_day(tx)
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
