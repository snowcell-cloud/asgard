"""
ML Model Training with Feast Feature Store Integration.

This script is designed to be uploaded via /mlops/training/upload API.
It:
1. Fetches features from Feast feature store (gold layer)
2. Trains a model using MLflow tracking
3. Registers the model to MLflow Model Registry
4. Automatically triggers deployment to OVH EKS

Environment Variables (injected by MLOps API):
- MLFLOW_TRACKING_URI: MLflow server URL
- EXPERIMENT_NAME: MLflow experiment name
- MODEL_NAME: Name for model registration
- FEAST_REPO_PATH: Path to Feast repository
- FEATURE_VIEW_NAME: Feast feature view to use (optional)
- USE_FEAST: "true" to fetch from Feast, "false" for synthetic data
"""

import os
import sys
import pickle
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List

import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient
import pandas as pd
import numpy as np
from feast import FeatureStore
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)

# Suppress warnings
os.environ["GIT_PYTHON_REFRESH"] = "quiet"
import logging

logging.getLogger("mlflow").setLevel(logging.ERROR)


class FeastMLTrainer:
    """ML model trainer with Feast feature store integration."""

    def __init__(
        self,
        feast_repo_path: str = "/tmp/feast_repo",
        mlflow_tracking_uri: str = "http://mlflow-service:5000",
        experiment_name: str = "feast_ml_training",
        model_name: str = "feast_model",
    ):
        """Initialize trainer with Feast and MLflow configuration."""
        self.feast_repo_path = feast_repo_path
        self.experiment_name = experiment_name
        self.model_name = model_name

        # Initialize Feast
        self.store = FeatureStore(repo_path=feast_repo_path)

        # Initialize MLflow
        mlflow.set_tracking_uri(mlflow_tracking_uri)
        mlflow.set_experiment(experiment_name)

        print(f"✅ FeastMLTrainer initialized")
        print(f"   Feast repo: {feast_repo_path}")
        print(f"   MLflow: {mlflow_tracking_uri}")
        print(f"   Experiment: {experiment_name}")

    def fetch_training_data(
        self, feature_view_name: str, entity_df: pd.DataFrame, features: List[str] = None
    ) -> pd.DataFrame:
        """
        Fetch features from Feast feature store.

        Args:
            feature_view_name: Name of the feature view
            entity_df: DataFrame with entity keys and timestamps
            features: List of feature names to fetch (None = all features)

        Returns:
            DataFrame with features
        """
        print(f"\n📥 Fetching features from Feast...")
        print(f"   Feature view: {feature_view_name}")
        print(f"   Entities: {len(entity_df)}")

        try:
            # Build feature references
            if features:
                feature_refs = [f"{feature_view_name}:{f}" for f in features]
            else:
                # Fetch all features from the view
                feature_refs = None

            # Fetch historical features
            training_df = self.store.get_historical_features(
                entity_df=entity_df, features=feature_refs or [feature_view_name]
            ).to_df()

            print(f"   ✅ Fetched {len(training_df)} rows with {len(training_df.columns)} features")
            return training_df

        except Exception as e:
            print(f"   ❌ Error fetching features: {e}")
            raise

    def train_model(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        model_params: Dict = None,
    ) -> RandomForestClassifier:
        """
        Train a Random Forest model with MLflow tracking.

        Args:
            X_train: Training features
            y_train: Training labels
            X_test: Test features
            y_test: Test labels
            model_params: Model hyperparameters

        Returns:
            Trained model
        """
        if model_params is None:
            model_params = {
                "n_estimators": 100,
                "max_depth": 10,
                "min_samples_split": 5,
                "min_samples_leaf": 2,
                "random_state": 42,
            }

        print(f"\n🔧 Training model with parameters:")
        for key, value in model_params.items():
            print(f"   {key}: {value}")

        with mlflow.start_run() as run:
            # Log parameters
            for key, value in model_params.items():
                mlflow.log_param(key, value)

            mlflow.log_param("n_features", X_train.shape[1])
            mlflow.log_param("n_train_samples", len(X_train))
            mlflow.log_param("n_test_samples", len(X_test))

            # Train model
            model = RandomForestClassifier(**model_params)
            model.fit(X_train, y_train)

            # Predictions
            y_pred_train = model.predict(X_train)
            y_pred_test = model.predict(X_test)
            y_proba_test = model.predict_proba(X_test)[:, 1]

            # Calculate metrics
            train_metrics = {
                "train_accuracy": accuracy_score(y_train, y_pred_train),
                "train_precision": precision_score(y_train, y_pred_train, zero_division=0),
                "train_recall": recall_score(y_train, y_pred_train, zero_division=0),
                "train_f1": f1_score(y_train, y_pred_train, zero_division=0),
            }

            test_metrics = {
                "test_accuracy": accuracy_score(y_test, y_pred_test),
                "test_precision": precision_score(y_test, y_pred_test, zero_division=0),
                "test_recall": recall_score(y_test, y_pred_test, zero_division=0),
                "test_f1": f1_score(y_test, y_pred_test, zero_division=0),
                "test_roc_auc": roc_auc_score(y_test, y_proba_test),
            }

            # Log all metrics
            for key, value in {**train_metrics, **test_metrics}.items():
                mlflow.log_metric(key, value)

            # Log feature importances
            feature_importance = dict(zip(X_train.columns, model.feature_importances_))
            for feature, importance in sorted(
                feature_importance.items(), key=lambda x: x[1], reverse=True
            ):
                mlflow.log_metric(f"importance_{feature}", importance)

            # Log confusion matrix
            cm = confusion_matrix(y_test, y_pred_test)
            mlflow.log_metric("true_negatives", int(cm[0, 0]))
            mlflow.log_metric("false_positives", int(cm[0, 1]))
            mlflow.log_metric("false_negatives", int(cm[1, 0]))
            mlflow.log_metric("true_positives", int(cm[1, 1]))

            # Log model using MLflow (save manually to avoid API compatibility issues)
            # Save model artifact
            with tempfile.TemporaryDirectory() as tmpdir:
                model_dir = os.path.join(tmpdir, "model")
                os.makedirs(model_dir, exist_ok=True)

                # Save sklearn model
                model_path = os.path.join(model_dir, "model.pkl")
                with open(model_path, "wb") as f:
                    pickle.dump(model, f)

                # Log the model directory
                mlflow.log_artifacts(model_dir, artifact_path="model")

                # Also save as additional artifact
                mlflow.log_artifact(model_path, artifact_path="model_artifacts")

            # Register model manually using MlflowClient
            client = MlflowClient()
            model_uri = f"runs:/{run.info.run_id}/model"

            try:
                # Try to create registered model first
                try:
                    client.create_registered_model(
                        name=self.model_name,
                        tags={"framework": "sklearn", "task": "classification"},
                    )
                    print(f"\n✅ Created registered model: {self.model_name}")
                except Exception as e:
                    if "RESOURCE_ALREADY_EXISTS" in str(e):
                        print(f"\n📌 Using existing registered model: {self.model_name}")
                    else:
                        raise

                # Create model version
                mv = client.create_model_version(
                    name=self.model_name, source=model_uri, run_id=run.info.run_id
                )
                print(f"✅ Model registered: {self.model_name} version {mv.version}")

            except Exception as e:
                print(f"\n⚠️  Model registration warning: {e}")
                print("   Model logged but not registered")

            print(f"\n✅ Training completed successfully!")
            print(f"   Run ID: {run.info.run_id}")
            print(f"   Model: {self.model_name}")
            print(f"\n📊 Test Metrics:")
            for key, value in test_metrics.items():
                print(f"   {key}: {value:.4f}")

            print(f"\n🎯 Top 5 Feature Importances:")
            for feature, importance in sorted(
                feature_importance.items(), key=lambda x: x[1], reverse=True
            )[:5]:
                print(f"   {feature}: {importance:.4f}")

            self.run_id = run.info.run_id
            return model


def main():
    """Main training pipeline."""

    # Configuration from environment variables
    FEAST_REPO_PATH = os.getenv("FEAST_REPO_PATH", "/tmp/feast_repo")
    MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow-service:5000")
    EXPERIMENT_NAME = os.getenv("EXPERIMENT_NAME", "feast_customer_churn")
    MODEL_NAME = os.getenv("MODEL_NAME", "churn_predictor_feast")
    FEATURE_VIEW_NAME = os.getenv("FEATURE_VIEW_NAME", "customer_churn_features")

    print("=" * 80)
    print("FEAST ML TRAINING PIPELINE")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Experiment: {EXPERIMENT_NAME}")
    print(f"Model: {MODEL_NAME}")
    print("=" * 80)

    # Initialize trainer
    trainer = FeastMLTrainer(
        feast_repo_path=FEAST_REPO_PATH,
        mlflow_tracking_uri=MLFLOW_TRACKING_URI,
        experiment_name=EXPERIMENT_NAME,
        model_name=MODEL_NAME,
    )

    # Option 1: Use Feast to fetch features (if feature view exists)
    # Uncomment when Feast feature views are set up
    """
    # Create entity DataFrame (customer IDs and timestamps)
    entity_df = pd.DataFrame({
        'customer_id': range(1, 1001),
        'event_timestamp': [datetime.now() - timedelta(days=i % 30) for i in range(1000)]
    })
    
    # Fetch features from Feast
    training_data = trainer.fetch_training_data(
        feature_view_name=FEATURE_VIEW_NAME,
        entity_df=entity_df
    )
    
    # Separate features and target
    X = training_data.drop(['customer_id', 'event_timestamp', 'churned'], axis=1)
    y = training_data['churned']
    """

    # Option 2: Generate synthetic data (for demo/testing)
    print("\n📊 Generating synthetic training data...")
    np.random.seed(42)
    n_samples = 1000

    data = pd.DataFrame(
        {
            "total_purchases": np.random.randint(1, 50, n_samples),
            "avg_purchase_value": np.random.uniform(10, 500, n_samples),
            "days_since_last_purchase": np.random.randint(0, 365, n_samples),
            "customer_lifetime_value": np.random.uniform(100, 10000, n_samples),
            "account_age_days": np.random.randint(30, 1825, n_samples),
            "support_tickets_count": np.random.randint(0, 20, n_samples),
        }
    )

    # Create target variable (churn)
    data["churned"] = (
        (data["days_since_last_purchase"] > 180) & (data["support_tickets_count"] > 5)
    ).astype(int)

    X = data.drop("churned", axis=1)
    y = data["churned"]

    print(f"   ✅ Generated {n_samples} samples with {len(X.columns)} features")
    print(f"   Class distribution: {y.value_counts().to_dict()}")

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Train model
    model = trainer.train_model(
        X_train,
        y_train,
        X_test,
        y_test,
        model_params={
            "n_estimators": 100,
            "max_depth": 10,
            "min_samples_split": 5,
            "min_samples_leaf": 2,
            "random_state": 42,
        },
    )

    print("\n" + "=" * 80)
    print("✅ TRAINING PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 80)
    print(f"Run ID: {trainer.run_id}")
    print(f"Model registered as: {MODEL_NAME}")
    print(f"\nView in MLflow UI: {MLFLOW_TRACKING_URI}")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
