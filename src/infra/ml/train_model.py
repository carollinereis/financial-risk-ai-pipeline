from pathlib import Path
from datetime import datetime

from src.infra.database.database import get_db_connection, bulk_update_risk_scores, init_db
from src.infra.ml.credit_risk_model import CreditRiskModel, HIGH_RISK_THRESHOLD, MODEL_VERSION

def run_training_pipeline():
    init_db()

    model_pipeline = CreditRiskModel()

    # 1. Load & prepare data from DuckDB
    df = model_pipeline.load_data()
    X = model_pipeline.prepare_features(df)
    y = model_pipeline.prepare_labels(df)

    # 2. Evaluate & Cross-Validate
    model_pipeline.evaluate(X, y)
    model_pipeline.cross_validate(X, y)

    # 3. Train on full dataset
    print("\n==================================================")
    print("TRAINING MODEL ON FULL DATASET & SCORING ALL CUSTOMERS")
    print("==================================================")
    model_pipeline.train(X, y)

    # 4. Score all customers & build persistence metadata
    df["risk_score"] = model_pipeline.predict_proba(X)
    df["is_high_risk_predicted"] = df["risk_score"] >= HIGH_RISK_THRESHOLD
    df["model_version"] = MODEL_VERSION
    df["scored_at"] = datetime.now()

    # 5. Save XGBoost native JSON artifact and bulk update DuckDB
    model_pipeline.save_model()
    
    with get_db_connection() as conn:
        bulk_update_risk_scores(conn, df)

    # 6. Sanity check: Print anchor profiles
    print("\n=== ANCHOR TEST PROFILES (SANITY CHECK) ===")
    anchors = df[df["customer_id"].isin([101, 102, 103, 104])][
        ["customer_id", "full_name", "credit_score", "debt_to_income_ratio", "risk_score", "is_high_risk_predicted"]
    ]
    print(anchors.to_string(index=False))


if __name__ == "__main__":
    run_training_pipeline()