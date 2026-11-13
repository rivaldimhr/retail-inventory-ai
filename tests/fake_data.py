"""Synthetic data in the exact Online Retail II format, for tests and offline development.

It is NOT used for any reported result: real results come from the real dataset.
"""
import numpy as np
import pandas as pd

PRODUCTS = [
    ("85123A", "WHITE HANGING HEART T-LIGHT HOLDER", 2.55),
    ("22423", "REGENCY CAKESTAND 3 TIER", 12.75),
    ("85099B", "JUMBO BAG RED RETROSPOT", 2.08),
    ("84879", "ASSORTED COLOUR BIRD ORNAMENT", 1.69),
    ("47566", "PARTY BUNTING", 4.95),
    ("20725", "LUNCH BAG RED RETROSPOT", 1.65),
    ("22720", "SET OF 3 CAKE TINS PANTRY DESIGN", 4.95),
    ("21212", "PACK OF 72 RETROSPOT CAKE CASES", 0.55),
    ("23084", "RABBIT NIGHT LIGHT", 2.08),
    ("22086", "PAPER CHAIN KIT 50'S CHRISTMAS", 2.95),
    ("22197", "SMALL POPCORN HOLDER", 0.85),
    ("21034", "REX CASH+CARRY JUMBO SHOPPER", 0.95),
    ("22382", "LUNCH BAG SPACEBOY DESIGN", 1.65),
    ("23203", "JUMBO BAG VINTAGE DOILY", 2.08),
    ("22457", "NATURAL SLATE HEART CHALKBOARD", 2.95),
    ("21931", "JUMBO STORAGE BAG SUKI", 2.08),
]
PAIRS = [("20725", "22382"), ("85099B", "23203"), ("22423", "22720"), ("21212", "22423")]


def make_raw(start="2009-12-01", end="2011-12-09", invoices_per_day=40, seed=7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    codes = [p[0] for p in PRODUCTS]
    info = {p[0]: p for p in PRODUCTS}
    popularity = rng.dirichlet(np.ones(len(codes)) * 2)
    rows, inv_no = [], 489434
    for day in pd.date_range(start, end, freq="D"):
        if day.dayofweek == 5:          # the real shop has no Saturday orders
            continue
        season = 1.0 + 1.5 * np.exp(-((day.dayofyear - 320) / 30) ** 2)   # pre-Christmas peak
        n_inv = rng.poisson(invoices_per_day * season)
        for _ in range(n_inv):
            inv_no += 1
            basket = set(rng.choice(codes, size=rng.integers(1, 5), replace=False, p=popularity))
            for a, b in PAIRS:
                if a in basket and rng.random() < 0.6:
                    basket.add(b)
            ts = day + pd.Timedelta(hours=int(rng.integers(8, 18)), minutes=int(rng.integers(0, 60)))
            for code in basket:
                _, desc, price = info[code]
                qty = int(rng.choice([1, 2, 3, 6, 12, 24], p=[.3, .2, .15, .15, .15, .05]))
                if "CHRISTMAS" in desc:
                    qty = int(qty * season * 2)
                rows.append([str(inv_no), code, desc, qty, ts, price, 13085.0, "United Kingdom"])
    df = pd.DataFrame(rows, columns=["Invoice", "StockCode", "Description", "Quantity",
                                     "InvoiceDate", "Price", "Customer ID", "Country"])
    noise = pd.DataFrame([
        ["C489449", "22423", "REGENCY CAKESTAND 3 TIER", -2, pd.Timestamp(start), 12.75, 13085.0, "United Kingdom"],
        ["489500", "POST", "POSTAGE", 1, pd.Timestamp(start), 18.0, 13085.0, "France"],
        ["489501", "M", "Manual", 1, pd.Timestamp(start), 5.0, 13085.0, "United Kingdom"],
        ["489502", "22423", "REGENCY CAKESTAND 3 TIER", 5, pd.Timestamp(start), 0.0, None, "United Kingdom"],
    ], columns=df.columns)
    return pd.concat([df, noise], ignore_index=True)
