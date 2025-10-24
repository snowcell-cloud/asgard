"""
Example Training Script 2: XGBoost Regression

This script demonstrates:
- Training an XGBoost regression model
- Using custom evaluation metrics
- Logging model with XGBoost flavor

Upload this script via:
POST /mlops/training/upload
{
  "script_name": "xgboost_regression",
  "script_content": "<base64 encoded content of this file>",
  "experiment_name": "xgboost_examples",
  "model_name": "xgb_regressor",
  "requirements": ["xgboost", "scikit-learn", "numpy"],
  "timeout": 300
}
"""

import mlflow
import mlflow.xgboost
import xgboost as xgb
from sklearn.datasets import make_regression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import numpy as np

# Generate synthetic regression dataset
print("Generating synthetic regression dataset...")
X, y = make_regression(n_samples=2000, n_features=30, n_informative=20, noise=10.0, random_state=42)

# Split data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print(f"Training set size: {len(X_train)}")
print(f"Test set size: {len(X_test)}")

# Start MLflow run
with mlflow.start_run():
    # Define hyperparameters
    params = {
        "objective": "reg:squarederror",
        "max_depth": 6,
        "learning_rate": 0.1,
        "n_estimators": 200,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42,
    }

    # Log parameters
    mlflow.log_params(params)

    # Create DMatrix for XGBoost
    dtrain = xgb.DMatrix(X_train, label=y_train)
    dtest = xgb.DMatrix(X_test, label=y_test)

    # Train model
    print("Training XGBoost model...")
    model = xgb.XGBRegressor(**params)
    model.fit(
        X_train, y_train, eval_set=[(X_test, y_test)], early_stopping_rounds=10, verbose=False
    )

    # Make predictions
    y_pred = model.predict(X_test)

    # Calculate metrics
    mse = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    print(f"RMSE: {rmse:.4f}")
    print(f"MAE: {mae:.4f}")
    print(f"R² Score: {r2:.4f}")

    # Log metrics
    mlflow.log_metric("mse", mse)
    mlflow.log_metric("rmse", rmse)
    mlflow.log_metric("mae", mae)
    mlflow.log_metric("r2_score", r2)

    # Log model (REQUIRED)
    mlflow.xgboost.log_model(model, "model", input_example=X_train[:5])

    # Log additional info
    mlflow.set_tag("model_type", "XGBRegressor")
    mlflow.set_tag("framework", "xgboost")
    mlflow.set_tag("task", "regression")

    print("✅ XGBoost model trained and logged successfully!")
