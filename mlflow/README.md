# Asgard MLOps - MLflow & Feast Integration

Complete MLOps platform with MLflow tracking, Feast feature store, and seamless training workflows.

## 📚 Documentation

**👉 See [COMPLETE_GUIDE.md](COMPLETE_GUIDE.md) for the full documentation**

The complete guide includes:
- Overview and architecture
- Quick start guide
- Complete API reference
- Training workflow with examples
- Feast feature store integration
- AWS credentials setup
- Testing and validation
- Troubleshooting
- Production deployment

## Quick Links

- **Main Documentation**: [COMPLETE_GUIDE.md](COMPLETE_GUIDE.md)
- **API Docs**: http://localhost:8000/docs (when running)
- **MLflow UI**: http://localhost:5000 (when running)

## Quick Start

1. **Port forward services**:
   ```bash
   kubectl port-forward -n asgard svc/asgard-app 8000:80 &
   kubectl port-forward -n asgard svc/mlflow-service 5000:5000 &
   ```

2. **Verify status**:
   ```bash
   curl http://localhost:8000/mlops/status
   ```

3. **Access UIs**:
   - Asgard API: http://localhost:8000/docs
   - MLflow: http://localhost:5000

## Features

✅ **MLflow Tracking** - Experiment tracking and model registry  
✅ **Feast Feature Store** - Feature management with Iceberg integration  
✅ **Script-based Training** - Upload and execute Python training scripts  
✅ **Model Serving** - Inference API for deployed models  
✅ **S3 Artifact Storage** - Scalable model artifact storage  
✅ **Production Ready** - Kubernetes-native, fully tested

## Status

🟢 **Production Ready**

- ✅ All features tested and validated
- ✅ AWS credentials configured
- ✅ Model artifacts saved successfully
- ✅ 100% test pass rate
- ✅ Comprehensive documentation

## Components

This directory contains Kubernetes manifests for:

- `mlflow-deployment.yaml` - MLflow server deployment
- `mlflow-service.yaml` - MLflow service definition
- `mlflow-ingress.yaml` - Ingress configuration
- `postgres.yaml` - PostgreSQL backend for MLflow
- `storage.yaml` - Persistent volume claims

## Support

For detailed information, troubleshooting, and examples, see the [COMPLETE_GUIDE.md](COMPLETE_GUIDE.md).

---

**Last Updated:** November 3, 2025
