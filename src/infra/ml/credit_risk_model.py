from pathlib import Path
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report, roc_auc_score

from src.domain.entities import CustomerProfile
from src.infra.config import MODEL_PATH 
from src.infra.database.database import get_db_connection

# Configuration Constants
FEATURE_COLUMNS = [
    "annual_income", 
    "credit_score", 
    "debt_to_income_ratio",
    "delinquencies_2yrs", 
    "loan_amount_requested", 
    "employment_length_years"
]
RANDOM_STATE = 42
TEST_SIZE = 0.2
CV_FOLDS = 5
HIGH_RISK_THRESHOLD = 0.65
MODEL_VERSION = "xgb_v1"


class CreditRiskModel:
    """Modular Machine Learning Pipeline for Financial Risk Scoring."""

    def __init__(self, model: XGBClassifier | None = None):
        self.model = model if model is not None else self.build_model()

    def build_model(self) -> XGBClassifier:
        """Returns an unfitted XGBClassifier instance."""
        return XGBClassifier(
            n_estimators=100,
            learning_rate=0.05,
            max_depth=4,
            random_state=RANDOM_STATE,
            eval_metric="logloss"
        )

    def load_data(self) -> pd.DataFrame:
        """Reads raw numerical features directly from DuckDB."""
        with get_db_connection() as conn:
            return conn.execute("SELECT * FROM customers").df()

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extracts feature matrix X."""
        return df[FEATURE_COLUMNS]

    def prepare_labels(self, df: pd.DataFrame) -> pd.Series:
        """Extracts ground-truth target label y."""
        return df["is_high_risk"]

    def evaluate(self, X: pd.DataFrame, y: pd.Series):
        """Holdout evaluation comparing Random Forest vs. XGBoost."""
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
        )

        print("\n==================================================")
        print("EVALUATION: ALGORITHM COMPARISON (RF vs. XGBOOST)")
        print("==================================================")

        # Baseline Random Forest
        rf = RandomForestClassifier(n_estimators=100, random_state=RANDOM_STATE)
        rf.fit(X_train, y_train)
        rf_auc = roc_auc_score(y_test, rf.predict_proba(X_test)[:, 1])
        print(f"Random Forest ROC-AUC Score: {rf_auc:.4f}")

        # XGBoost Classifier
        xgb = self.build_model()
        xgb.fit(X_train, y_train)
        xgb_proba = xgb.predict_proba(X_test)[:, 1]
        xgb_auc = roc_auc_score(y_test, xgb_proba)
        print(f"XGBoost Classifier ROC-AUC Score: {xgb_auc:.4f}")

        # Classification Metrics at Threshold
        xgb_preds = (xgb_proba >= HIGH_RISK_THRESHOLD).astype(int)
        print(f"\nXGBoost Classification Metrics (Threshold = {HIGH_RISK_THRESHOLD}):")
        print(classification_report(y_test, xgb_preds, target_names=["Low Risk", "High Risk"]))

    def cross_validate(self, X: pd.DataFrame, y: pd.Series):
        """Runs Stratified 5-Fold Cross Validation using fresh model instances."""
        print("==================================================")
        print(f"EVALUATION: {CV_FOLDS}-FOLD STRATIFIED CROSS-VALIDATION")
        print("==================================================")

        skf = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
        cv_scores = cross_val_score(self.build_model(), X, y, cv=skf, scoring="roc_auc")

        print(f"{CV_FOLDS}-Fold ROC-AUC Scores: {[round(s, 4) for s in cv_scores]}")
        print(f"Mean CV ROC-AUC Score: {cv_scores.mean():.4f} (± {cv_scores.std():.4f})")

    def train(self, X: pd.DataFrame, y: pd.Series):
        """Fits the primary model on supplied feature set."""
        self.model.fit(X, y)

    def predict_proba(self, X: pd.DataFrame) -> pd.Series:
        """Returns 0.0–1.0 risk probability scores."""
        return self.model.predict_proba(X)[:, 1]

    def predict_risk(self, profile: CustomerProfile) -> float:
        """
        Domain-layer bridge: Maps CustomerProfile attributes -> FEATURE_COLUMNS,
        and computes predicted default probability score.
        """
        feature_dict = {
            "annual_income": profile.income,
            "credit_score": profile.credit_score,
            "debt_to_income_ratio": profile.dti,
            "delinquencies_2yrs": profile.delinquencies,
            "loan_amount_requested": profile.loan_amount,
            "employment_length_years": getattr(profile, "employment_length_years", None) or 3,
        }

        # Build 1-row DataFrame aligned with exact FEATURE_COLUMNS order
        features_df = pd.DataFrame([feature_dict])[FEATURE_COLUMNS]
        
        # Predict probability for positive class (Default / High Risk = 1)
        prob = self.predict_proba(features_df)[0]
        return float(prob)

    def save_model(self, path: Path | str | None = None) -> Path:
        """Persists trained model artifact in XGBoost native JSON format."""
        output_path = Path(path) if path is not None else MODEL_PATH
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.model.save_model(str(output_path))
        print(f"Saved model artifact to {output_path}")
        return output_path

    @classmethod
    def load_model(cls, path: Path | str | None = None) -> "CreditRiskModel":
        """Loads a trained model artifact and returns a CreditRiskModel wrapper instance."""
        model_path = Path(path) if path is not None else MODEL_PATH
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model file not found at {model_path}. Run training script first."
            )
        
        instance = cls()
        instance.model.load_model(str(model_path))
        return instance


if __name__ == "__main__":
    # Script execution flow for model training
    model = CreditRiskModel()
    raw_df = model.load_data()
    
    X = model.prepare_features(raw_df)
    y = model.prepare_labels(raw_df)
    
    model.evaluate(X, y)
    model.cross_validate(X, y)
    
    print("\nFitting final model on full dataset...")
    model.train(X, y)
    model.save_model()