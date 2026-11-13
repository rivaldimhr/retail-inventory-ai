"""Market basket analysis on real invoices.

Each invoice is one basket. Rules are product pairs "A -> B" with support, confidence and lift,
the same measures Apriori produces for 2-item rules, computed directly with a sparse
co-occurrence matrix (fast, no extra dependency).
"""
from datetime import datetime

import numpy as np
import pandas as pd
from scipy import sparse

from src.config.config import config


def run(tx: pd.DataFrame, min_support=None, min_confidence=None, min_lift=None, top_n=None) -> dict:
    min_support = config.MBA_MIN_SUPPORT if min_support is None else min_support
    min_confidence = config.MBA_MIN_CONFIDENCE if min_confidence is None else min_confidence
    min_lift = config.MBA_MIN_LIFT if min_lift is None else min_lift
    top_n = config.MBA_TOP_N_PRODUCTS if top_n is None else top_n

    params = {"min_support": min_support, "min_confidence": min_confidence, "min_lift": min_lift, "products_considered": top_n}
    pairs = tx[["invoice", "stock_code"]].drop_duplicates()
    top = pairs["stock_code"].value_counts().head(top_n).index
    pairs = pairs[pairs["stock_code"].isin(top)]
    total_invoices = int(tx["invoice"].nunique())

    inv_codes, inv_idx = np.unique(pairs["invoice"].to_numpy(), return_inverse=True)
    prod_codes, prod_idx = np.unique(pairs["stock_code"].to_numpy(), return_inverse=True)
    x = sparse.csr_matrix((np.ones(len(pairs), dtype=np.int32), (inv_idx, prod_idx)),
                          shape=(len(inv_codes), len(prod_codes)))
    n = total_invoices
    item_count = np.asarray(x.sum(axis=0)).ravel()
    co = (x.T @ x).tocoo()

    a, b, c = co.row, co.col, co.data
    keep = (a != b) & (c / n >= min_support)
    a, b, c = a[keep], b[keep], c[keep]
    support = c / n
    confidence = c / item_count[a]
    lift = confidence / (item_count[b] / n)
    keep = (confidence >= min_confidence) & (lift >= min_lift)

    names = tx.drop_duplicates("stock_code").set_index("stock_code")["description"].str.title()
    rules = pd.DataFrame({
        "a": prod_codes[a[keep]], "b": prod_codes[b[keep]], "count": c[keep],
        "support": support[keep], "confidence": confidence[keep], "lift": lift[keep],
    }).sort_values(["lift", "support"], ascending=False).head(config.MBA_MAX_RULES)

    rules_list = [
        {
            "antecedents": [names.get(r.a, r.a)],
            "consequents": [names.get(r.b, r.b)],
            "antecedent_codes": [r.a],
            "consequent_codes": [r.b],
            "transactions": int(r.count),
            "support": round(float(r.support), 4),
            "confidence": round(float(r.confidence), 4),
            "lift": round(float(r.lift), 3),
        }
        for r in rules.itertuples(index=False)
    ]
    return {
        "generated_at": datetime.now().isoformat(),
        "parameters": params,
        "rules": rules_list,
        "summary": {
            "total_rules": len(rules_list),
            "total_transactions": total_invoices,
            "total_products": int(tx["stock_code"].nunique()),
        },
    }
