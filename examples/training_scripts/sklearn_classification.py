"""
Example Training Script 1: Simple Sklearn Classification

This script demonstrates:
- Loading data
- Training a Random Forest classifier
- Logging parameters, metrics, and model to MLflow

Upload this script via:
POST /mlops/training/upload
{
  "script_name": "sklearn_classification",
  "script_content": "<base64 encoded content of this file>",
  "experiment_name": "sklearn_examples",
  "model_name": "random_forest_classifier",
  "requirements": ["scikit-learn", "pandas", "numpy"],
  "timeout": 300
}
"""

import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import pandas as pd
import numpy as np

# Generate synthetic dataset
print("Generating synthetic dataset...")
X, y = make_classification(
    n_samples=1000, n_features=20, n_informative=15, n_redundant=5, n_classes=2, random_state=42
)

# Split data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print(f"Training set size: {len(X_train)}")
print(f"Test set size: {len(X_test)}")

# Start MLflow run (MLflow URI is already configured by the platform)
with mlflow.start_run():
    # Define hyperparameters
    params = {"n_estimators": 100, "max_depth": 10, "min_samples_split": 2, "random_state": 42}

    # Log parameters
    mlflow.log_params(params)

    # Train model
    print("Training Random Forest model...")
    model = RandomForestClassifier(**params)
    model.fit(X_train, y_train)

    # Make predictions
    y_pred = model.predict(X_test)

    # Calculate metrics
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, average="weighted")
    recall = recall_score(y_test, y_pred, average="weighted")
    f1 = f1_score(y_test, y_pred, average="weighted")

    print(f"Accuracy: {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall: {recall:.4f}")
    print(f"F1 Score: {f1:.4f}")

    # Log metrics
    mlflow.log_metric("accuracy", accuracy)
    mlflow.log_metric("precision", precision)
    mlflow.log_metric("recall", recall)
    mlflow.log_metric("f1_score", f1)

    # Log model (REQUIRED - this makes it available for inference)
    mlflow.sklearn.log_model(
        model,
        "model",
        input_example=X_train[:5],
        signature=mlflow.models.infer_signature(X_train, y_pred),
    )

    # Log additional info
    mlflow.set_tag("model_type", "RandomForestClassifier")
    mlflow.set_tag("framework", "sklearn")

    print("✅ Model trained and logged successfully!")
