# Example Training Scripts for MLOps Deploy API

This document provides example training scripts that you can use with the `/mlops/deploy` API endpoint.

## 📋 Requirements

Your training script **MUST**:

1. ✅ Call `mlflow.start_run()` to create an MLflow run
2. ✅ Train your model
3. ✅ Call `mlflow.<framework>.log_model(model, 'model')` to save the model
4. ✅ The model will be automatically registered in MLflow Model Registry

## 🚀 Quick Start Example

### Minimal Scikit-learn Example

```python
import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split

# Create sample dataset
X, y = make_classification(n_samples=1000, n_features=20, n_classes=2, random_state=42)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train and log model
with mlflow.start_run():
    # Train model
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # Log parameters
    mlflow.log_params({
        'n_estimators': 100,
        'max_depth': None,
        'random_state': 42
    })

    # Log metrics
    train_score = model.score(X_train, y_train)
    test_score = model.score(X_test, y_test)
    mlflow.log_metrics({
        'train_accuracy': train_score,
        'test_accuracy': test_score
    })

    # Log model - THIS IS REQUIRED!
    mlflow.sklearn.log_model(model, 'model')

    print(f"✅ Model trained! Train accuracy: {train_score:.4f}, Test accuracy: {test_score:.4f}")
```

### API Request Example

```bash
# First, base64 encode your script
cat train_script.py | base64 > script_encoded.txt

# Or use Python to encode
python3 << 'EOF'
import base64

script = '''
import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split

X, y = make_classification(n_samples=1000, n_features=20, n_classes=2, random_state=42)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

with mlflow.start_run():
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    mlflow.log_params({'n_estimators': 100})
    mlflow.log_metric('accuracy', model.score(X_test, y_test))
    mlflow.sklearn.log_model(model, 'model')
    print("Model trained successfully!")
'''

encoded = base64.b64encode(script.encode()).decode()
print(encoded)
EOF

# Then deploy
curl -X POST "http://localhost:8000/mlops/deploy" \
  -H "Content-Type: application/json" \
  -d '{
    "script_name": "train_rf_model.py",
    "script_content": "<BASE64_ENCODED_SCRIPT>",
    "experiment_name": "production",
    "model_name": "customer_churn_model",
    "requirements": ["scikit-learn==1.3.2", "pandas==2.1.3", "numpy==1.26.2"],
    "timeout": 300,
    "replicas": 2,
    "namespace": "asgard"
  }'
```

## 📚 More Examples

### XGBoost Example

```python
import mlflow
import mlflow.xgboost
import xgboost as xgb
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split

# Create dataset
X, y = make_classification(n_samples=1000, n_features=20, n_classes=2, random_state=42)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Convert to DMatrix
dtrain = xgb.DMatrix(X_train, label=y_train)
dtest = xgb.DMatrix(X_test, label=y_test)

# Train with MLflow
with mlflow.start_run():
    params = {
        'max_depth': 6,
        'eta': 0.3,
        'objective': 'binary:logistic',
        'eval_metric': 'auc'
    }

    mlflow.log_params(params)

    model = xgb.train(params, dtrain, num_boost_round=100)

    # Log model - REQUIRED!
    mlflow.xgboost.log_model(model, 'model')

    print("✅ XGBoost model trained and logged!")
```

**Requirements**: `["xgboost==2.0.3", "scikit-learn==1.3.2", "numpy==1.26.2"]`

### LightGBM Example

```python
import mlflow
import mlflow.lightgbm
import lightgbm as lgb
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split

# Create dataset
X, y = make_classification(n_samples=1000, n_features=20, n_classes=2, random_state=42)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Create datasets
train_data = lgb.Dataset(X_train, label=y_train)
test_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

# Train with MLflow
with mlflow.start_run():
    params = {
        'objective': 'binary',
        'metric': 'binary_logloss',
        'num_leaves': 31,
        'learning_rate': 0.05
    }

    mlflow.log_params(params)

    model = lgb.train(
        params,
        train_data,
        num_boost_round=100,
        valid_sets=[test_data]
    )

    # Log model - REQUIRED!
    mlflow.lightgbm.log_model(model, 'model')

    print("✅ LightGBM model trained and logged!")
```

**Requirements**: `["lightgbm==4.1.0", "scikit-learn==1.3.2", "numpy==1.26.2"]`

### Model with Feature Engineering

```python
import mlflow
import mlflow.sklearn
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split

# Create dataset
X, y = make_classification(n_samples=1000, n_features=20, n_classes=2, random_state=42)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Create pipeline with preprocessing
with mlflow.start_run():
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('classifier', RandomForestClassifier(n_estimators=100, random_state=42))
    ])

    # Train
    pipeline.fit(X_train, y_train)

    # Log parameters
    mlflow.log_params({
        'n_estimators': 100,
        'preprocessing': 'StandardScaler',
        'model_type': 'RandomForest'
    })

    # Log metrics
    train_score = pipeline.score(X_train, y_train)
    test_score = pipeline.score(X_test, y_test)
    mlflow.log_metrics({
        'train_accuracy': train_score,
        'test_accuracy': test_score
    })

    # Log the entire pipeline - REQUIRED!
    mlflow.sklearn.log_model(pipeline, 'model')

    print(f"✅ Pipeline model trained! Test accuracy: {test_score:.4f}")
```

**Requirements**: `["scikit-learn==1.3.2", "pandas==2.1.3", "numpy==1.26.2"]`

## 🔍 Troubleshooting

### Common Errors

#### Error: "No MLflow runs found after training"

**Cause**: Your script didn't call `mlflow.start_run()`

**Solution**:

```python
with mlflow.start_run():
    # Your training code here
    mlflow.sklearn.log_model(model, 'model')
```

#### Error: "No model artifact found in run"

**Cause**: You didn't call `mlflow.<framework>.log_model()`

**Solution**:

- Scikit-learn: `mlflow.sklearn.log_model(model, 'model')`
- XGBoost: `mlflow.xgboost.log_model(model, 'model')`
- LightGBM: `mlflow.lightgbm.log_model(model, 'model')`
- TensorFlow: `mlflow.tensorflow.log_model(model, 'model')`
- PyTorch: `mlflow.pytorch.log_model(model, 'model')`

#### Error: "Training script failed with exit code 1"

**Cause**: Your script has a Python error

**Solution**: Check the error output in the API response for details

## 📝 Script Template

Use this template as a starting point:

```python
import mlflow
import mlflow.sklearn  # Change framework as needed
from sklearn.ensemble import RandomForestClassifier  # Your model
from sklearn.datasets import make_classification  # Your data loading
from sklearn.model_selection import train_test_split

# 1. Load or create your data
X, y = make_classification(n_samples=1000, n_features=20, n_classes=2)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# 2. Start MLflow run
with mlflow.start_run():
    # 3. Train your model
    model = RandomForestClassifier(n_estimators=100)
    model.fit(X_train, y_train)

    # 4. Log parameters (optional but recommended)
    mlflow.log_params({'n_estimators': 100})

    # 5. Log metrics (optional but recommended)
    accuracy = model.score(X_test, y_test)
    mlflow.log_metric('accuracy', accuracy)

    # 6. Log model - REQUIRED!
    mlflow.sklearn.log_model(model, 'model')

    print(f"✅ Model trained! Accuracy: {accuracy:.4f}")
```

## 🎯 Complete Deployment Flow

1. **Write your training script** (see examples above)
2. **Base64 encode it**:
   ```python
   import base64
   with open('train.py', 'rb') as f:
       encoded = base64.b64encode(f.read()).decode()
   ```
3. **Send deployment request**:
   ```bash
   curl -X POST "http://localhost:8000/mlops/deploy" \
     -H "Content-Type: application/json" \
     -d '{
       "script_name": "train.py",
       "script_content": "'$encoded'",
       "experiment_name": "production",
       "model_name": "my_model",
       "requirements": ["scikit-learn==1.3.2"],
       "timeout": 300,
       "replicas": 2
     }'
   ```
4. **Wait for response** (includes inference URL)
5. **Make predictions**:
   ```bash
   curl -X POST "http://<EXTERNAL_IP>/predict" \
     -H "Content-Type: application/json" \
     -d '{
       "inputs": {
         "feature1": [1.0, 2.0, 3.0],
         "feature2": [4.0, 5.0, 6.0]
       }
     }'
   ```

## 🔗 Related Documentation

- [MLOps API Guide](./MLOPS_API_FINAL.md)
- [Quick Reference](./MLOPS_QUICK_REFERENCE.md)
- [API Testing Guide](./API_TESTING_GUIDE.md)
