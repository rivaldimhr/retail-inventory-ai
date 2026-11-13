"""Load and clean the Online Retail II dataset (UCI, CC BY 4.0).

Raw columns (xlsx / csv): Invoice, StockCode, Description, Quantity, InvoiceDate, Price, Customer ID, Country.
Older exports use InvoiceNo / UnitPrice / CustomerID; both spellings are accepted.
"""
import os
import re

import pandas as pd

COLUMN_ALIASES = {
    "invoice": "invoice", "invoiceno": "invoice",
    "stockcode": "stock_code",
    "description": "description",
    "quantity": "quantity",
    "invoicedate": "invoice_date",
    "price": "price", "unitprice": "price",
    "customerid": "customer_id",
    "country": "country",
}

# Real products have a 5-digit code, optionally followed by letters (e.g. 85123A).
# Everything else is postage, fees, adjustments or manual entries (POST, DOT, M, BANK CHARGES, ...).
PRODUCT_CODE = re.compile(r"^\d{5}[A-Z]*$")


def read_raw(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Dataset not found at {path}. Download Online Retail II from "
            "https://archive.ics.uci.edu/dataset/502/online+retail+ii and place it in data/."
        )
    if path.lower().endswith((".xlsx", ".xls")):
        sheets = pd.read_excel(path, sheet_name=None, dtype={"Invoice": str, "StockCode": str})
        df = pd.concat(sheets.values(), ignore_index=True)
    else:
        df = pd.read_csv(path, dtype={"Invoice": str, "InvoiceNo": str, "StockCode": str}, encoding_errors="replace")
    return normalize_columns(df)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename = {}
    for col in df.columns:
        key = re.sub(r"[^a-z]", "", str(col).lower())
        if key in COLUMN_ALIASES:
            rename[col] = COLUMN_ALIASES[key]
    df = df.rename(columns=rename)
    missing = {"invoice", "stock_code", "description", "quantity", "invoice_date", "price"} - set(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing columns: {sorted(missing)}")
    return df


def clean_transactions(df: pd.DataFrame, country: str = "") -> pd.DataFrame:
    """Keep completed sales lines of real products.

    Removes: cancellations (invoice starting with 'C'), non-positive quantity or price,
    missing descriptions, non-product stock codes, and exact duplicate lines.
    """
    df = df.copy()
    df["invoice"] = df["invoice"].astype(str).str.strip()
    df["stock_code"] = df["stock_code"].astype(str).str.strip().str.upper()
    df["description"] = df["description"].astype(str).str.strip().str.upper()
    df["invoice_date"] = pd.to_datetime(df["invoice_date"], errors="coerce")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")

    mask = (
        ~df["invoice"].str.upper().str.startswith("C")
        & (df["quantity"] > 0)
        & (df["price"] > 0)
        & df["invoice_date"].notna()
        & df["description"].ne("")
        & df["description"].ne("NAN")
        & df["stock_code"].str.match(PRODUCT_CODE)
    )
    if country:
        mask &= df["country"].astype(str).str.strip().eq(country)
    df = df.loc[mask].drop_duplicates()

    # One canonical name per product: the most frequent description.
    names = (
        df.groupby(["stock_code", "description"]).size().reset_index(name="n")
        .sort_values(["stock_code", "n"], ascending=[True, False])
        .drop_duplicates("stock_code")
        .set_index("stock_code")["description"]
    )
    df["description"] = df["stock_code"].map(names)
    df["date"] = df["invoice_date"].dt.normalize()
    cols = ["invoice", "stock_code", "description", "quantity", "price", "invoice_date", "date"]
    if "customer_id" in df.columns:
        cols.append("customer_id")
    if "country" in df.columns:
        cols.append("country")
    return df[cols].reset_index(drop=True)
