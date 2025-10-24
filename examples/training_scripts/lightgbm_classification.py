"""
Example Training Script 3: LightGBM with Custom Data

This script demonstrates:
- Loading data from environment variables
- Training a LightGBM model
- Logging feature importances

Upload this script via:
POST /mlops/training/upload
{
  "script_name": "lightgbm_classifier",
  "script_content": "<base64 encoded content of this file>",
  "experiment_name": "lightgbm_examples",
  "model_name": "lgbm_classifier",
  "requirements": ["lightgbm", "scikit-learn", "pandas", "matplotlib"],
  "environment_vars": {
    "N_SAMPLES": "5000",
    "N_FEATURES": "25"
  },
  "timeout": 300
}
"""

import os
import mlflow
import mlflow.lightgbm
import lightgbm as lgb
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, log_loss
import pandas as pd
import numpy as np

# Get configuration from environment variables
n_samples = int(os.getenv("N_SAMPLES", "1000"))
n_features = int(os.getenv("N_FEATURES", "20"))

print(f"Configuration from environment:")
print(f"  N_SAMPLES: {n_samples}")
print(f"  N_FEATURES: {n_features}")

# Generate dataset
print("Generating dataset...")
X, y = make_classification(
    n_samples=n_samples,
    n_features=n_features,
    n_informative=int(n_features * 0.7),
    n_redundant=int(n_features * 0.3),
    n_classes=2,
    random_state=42,
)

# Create feature names
feature_names = [f"feature_{i}" for i in range(n_features)]
X_df = pd.DataFrame(X, columns=feature_names)

# Split data
X_train, X_test, y_train, y_test = train_test_split(X_df, y, test_size=0.2, random_state=42)

print(f"Training set size: {len(X_train)}")
print(f"Test set size: {len(X_test)}")

# Start MLflow run
with mlflow.start_run():
    # Define hyperparameters
    params = {
        "objective": "binary",
        "metric": "binary_logloss",
        "boosting_type": "gbdt",
        "num_leaves": 31,
        "learning_rate": 0.05,
        "n_estimators": 100,
        "feature_fraction": 0.9,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "random_state": 42,
    }

    # Log parameters
    mlflow.log_params(params)
    mlflow.log_param("n_samples", n_samples)
    mlflow.log_param("n_features", n_features)

    # Train model
    print("Training LightGBM model...")
    model = lgb.LGBMClassifier(**params)
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_test, y_test)],
        eval_metric="logloss",
        # early_stopping_rounds=10,
        verbose=False,
    )

    # Make predictions
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]

    # Calculate metrics
    accuracy = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_pred_proba)
    logloss = log_loss(y_test, y_pred_proba)

    print(f"Accuracy: {accuracy:.4f}")
    print(f"AUC-ROC: {auc:.4f}")
    print(f"Log Loss: {logloss:.4f}")

    # Log metrics
    mlflow.log_metric("accuracy", accuracy)
    mlflow.log_metric("auc_roc", auc)
    mlflow.log_metric("log_loss", logloss)

    # Log feature importances
    feature_importance = pd.DataFrame(
        {"feature": feature_names, "importance": model.feature_importances_}
    ).sort_values("importance", ascending=False)

    print("\nTop 10 features:")
    print(feature_importance.head(10))

    # Save feature importance as artifact
    feature_importance.to_csv("/tmp/feature_importance.csv", index=False)
    mlflow.log_artifact("/tmp/feature_importance.csv")

    # Log model (REQUIRED)
    mlflow.lightgbm.log_model(model, "model", input_example=X_train.head(5))

    # Log additional info
    mlflow.set_tag("model_type", "LGBMClassifier")
    mlflow.set_tag("framework", "lightgbm")
    mlflow.set_tag("task", "binary_classification")

    print("✅ LightGBM model trained and logged successfully!")
