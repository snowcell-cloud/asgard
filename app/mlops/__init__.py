"""
MLOps module for ML lifecycle management.

Integrates:
- Feast: Feature engineering and serving
- MLflow: Experiment tracking, model training, and registry
- Model serving: Predictions with feature transformation
"""

from app.mlops.router import router

__all__ = ["router"]
