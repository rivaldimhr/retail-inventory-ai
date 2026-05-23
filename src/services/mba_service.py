import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder
from datetime import datetime


class MBAService:
    @staticmethod
    def run(df_raw, min_support=0.001, min_confidence=0.1, min_lift=1.0):
        # Setiap kombinasi Member+Date dianggap 1 keranjang belanja
        baskets = (
            df_raw.groupby(["Member_number", "Date"])["itemDescription"]
            .apply(list)
            .tolist()
        )

        te = TransactionEncoder()
        te_array = te.fit_transform(baskets)
        df_encoded = pd.DataFrame(te_array, columns=te.columns_)

        frequent_itemsets = apriori(
            df_encoded, min_support=min_support, use_colnames=True
        )

        summary = {
            "total_transactions": len(baskets),
            "total_products": len(te.columns_),
        }

        if frequent_itemsets.empty:
            return {
                "generated_at": datetime.now().isoformat(),
                "parameters": {
                    "min_support": min_support,
                    "min_confidence": min_confidence,
                    "min_lift": min_lift,
                },
                "rules": [],
                "summary": {**summary, "total_rules": 0},
            }

        rules = association_rules(
            frequent_itemsets,
            num_itemsets=len(df_encoded),
            metric="confidence",
            min_threshold=min_confidence,
        )
        rules = rules[rules["lift"] >= min_lift].sort_values("lift", ascending=False)

        rules_list = [
            {
                "antecedents": sorted(list(row["antecedents"])),
                "consequents": sorted(list(row["consequents"])),
                "support": round(float(row["support"]), 4),
                "confidence": round(float(row["confidence"]), 4),
                "lift": round(float(row["lift"]), 4),
            }
            for _, row in rules.iterrows()
        ]

        return {
            "generated_at": datetime.now().isoformat(),
            "parameters": {
                "min_support": min_support,
                "min_confidence": min_confidence,
                "min_lift": min_lift,
            },
            "rules": rules_list,
            "summary": {**summary, "total_rules": len(rules_list)},
        }
