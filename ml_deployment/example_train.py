"""
Example training script for MLOps deployment.

This is a minimal working example that demonstrates:
1. Creating a dataset
2. Training a model
3. Logging with MLflow
4. Registering the model

You can use this as a template for your own training scripts.
"""

import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

print("🚀 Starting model training...")

# Create sample dataset
print("📊 Creating dataset...")
X, y = make_classification(
    n_samples=1000, n_features=20, n_informative=15, n_redundant=5, n_classes=2, random_state=42
)

# Split data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print(f"   Training samples: {len(X_train)}")
print(f"   Test samples: {len(X_test)}")
print(f"   Features: {X_train.shape[1]}")

# Train model with MLflow tracking
print("🎯 Training model...")
with mlflow.start_run():
    # Define model parameters
    params = {
        "n_estimators": 100,
        "max_depth": 10,
        "min_samples_split": 5,
        "min_samples_leaf": 2,
        "random_state": 42,
    }

    # Log parameters
    mlflow.log_params(params)

    # Train model
    model = RandomForestClassifier(**params)
    model.fit(X_train, y_train)

    # Make predictions
    y_train_pred = model.predict(X_train)
    y_test_pred = model.predict(X_test)

    # Calculate metrics
    metrics = {
        "train_accuracy": accuracy_score(y_train, y_train_pred),
        "test_accuracy": accuracy_score(y_test, y_test_pred),
        "test_precision": precision_score(y_test, y_test_pred),
        "test_recall": recall_score(y_test, y_test_pred),
        "test_f1": f1_score(y_test, y_test_pred),
    }

    # Log metrics
    mlflow.log_metrics(metrics)

    # Log model - THIS IS REQUIRED!
    mlflow.sklearn.log_model(model, "model")

    # Print results
    print("\n📈 Training Results:")
    print(f"   Train Accuracy: {metrics['train_accuracy']:.4f}")
    print(f"   Test Accuracy:  {metrics['test_accuracy']:.4f}")
    print(f"   Precision:      {metrics['test_precision']:.4f}")
    print(f"   Recall:         {metrics['test_recall']:.4f}")
    print(f"   F1 Score:       {metrics['test_f1']:.4f}")

    print("\n✅ Model trained and logged successfully!")
