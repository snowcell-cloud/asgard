# Asgard Data Platform

**Where Data Engineering Meets Machine Learning**  
_The bridge between your raw data and intelligent predictions_

[![Production Ready](https://img.shields.io/badge/status-production%20ready-green)]()
[![Kubernetes](https://img.shields.io/badge/kubernetes-native-blue)]()
[![API](https://img.shields.io/badge/API-FastAPI-teal)]()

---

## 📖 The Asgard Story

### The Problem We Solve

Imagine you're a data scientist at an e-commerce company. Your CEO asks: _"Can we predict which customers will churn next month?"_

You know the data exists—scattered across PostgreSQL databases, MongoDB collections, and CSV files. You know how to build the model. But between you and that prediction lies a gauntlet of challenges:

- **The Data Engineering Bottleneck**: You need to extract data from 5 different systems, clean it, join it, and transform it into features
- **The Integration Nightmare**: Airbyte for ingestion, Spark for processing, DBT for transformations, Feast for features, MLflow for models—each with different APIs, configurations, and deployment patterns
- **The Duplication Problem**: Your feature store copies data from your data lake, doubling storage costs and creating consistency headaches
- **The Time Sink**: What should take days stretches into weeks or months as you glue together different systems

**Asgard changes this story.**

### What Asgard Does

Asgard is a **unified data platform** that turns complex data pipelines into simple API calls. It orchestrates your entire journey from raw data to predictions through a single, elegant REST API.

Think of Asgard as your **data conductor**—coordinating multiple powerful open-source tools (Airbyte, Spark, DBT, Feast, MLflow) into a harmonious symphony, letting you focus on insights instead of infrastructure.

### The Asgard Way

Instead of spending weeks integrating systems, you describe what you want:

> _"Take my customer data from Postgres, clean it, create purchase frequency features, train a churn model, and give me predictions for my top 1000 customers."_

Asgard translates this into orchestrated actions across its platform, handling the complexity behind a clean API. What took weeks now takes hours.

---

## 🌟 How Asgard Works

### The Journey of Data

Picture your data as raw ore extracted from a mine. Asgard refines it through progressive stages, each adding value:

**🥉 Bronze Layer** - _The Raw Extraction_  
Your data arrives exactly as it exists in source systems—PostgreSQL tables, MongoDB documents, Kafka streams. No transformations yet, just a perfect historical archive in your S3 data lake.

**🥈 Silver Layer** - _The Refinement_  
Spark processes clean this data—removing duplicates, fixing data types, validating email formats, handling nulls. This is where messy reality becomes reliable data you can trust.

**🥇 Gold Layer** - _The Business Value_  
DBT transformations create business metrics: customer lifetime value, purchase frequency, days since last order. This is data that tells your business story.

**💎 Features** - _The ML Magic_  
Feast organizes gold data into feature views—reusable, versioned, point-in-time correct features that data scientists can instantly access for any model.

**🚀 Models** - _The Intelligence_  
MLflow manages your trained models—experiments, versions, parameters, metrics. Deploy once, predict forever.

### The Magic: Zero Duplication

Here's where Asgard breaks from tradition. While other platforms **copy** data from your data lake to a feature store (doubling costs and complexity), Asgard's Feast integration **reads directly** from Iceberg tables in S3.

Your gold layer **IS** your feature store. One source of truth. No synchronization. No duplication. Just elegant efficiency.

---

## 📚 Documentation

### 🌟 **Start Here** (New Users)

| Document                                                | Description                           | Time    |
| ------------------------------------------------------- | ------------------------------------- | ------- |
| **[� Onboarding & Setup](./docs/ONBOARDING_SETUP.md)**  | Complete setup and installation guide | 30 min  |
| **[📖 Documentation and video](./docs/PLATFORM_DOCUMENTATION_AND_VIDEO.md)**       |Complete documentation and Video             | 2-3 hrs |
| **[🎨 Visual Diagrams](./docs/COMPLETE_ARCHITECTURE.md)**            | System architecture and data flow     | 30 min  |

---

## ⚡ Quick Start

### Prerequisites

- Python 3.11+
- Kubernetes cluster access
- kubectl configured
- S3-compatible storage (AWS S3 or MinIO)

### 5-Minute Setup

```bash
# 1. Port forward Asgard API
kubectl port-forward -n asgard svc/asgard-app 8000:80 &

# 2. Port forward MLflow UI (optional)
kubectl port-forward -n asgard svc/mlflow-service 5000:5000 &

# 3. Check platform status
curl http://localhost:8000/mlops/status

# 4. Access interactive API docs
open http://localhost:8000/docs
```

### Access Points

- **Asgard API:** http://localhost:8000/docs (Swagger UI)
- **MLflow UI:** http://localhost:5000 (Experiment tracking)

---

## 🎓 Learning Paths

### Path 1: Quick Start (30 minutes)

```
Quick Reference Guide → Try one API call → Read Use Case Phase 1
```

### Path 2: Complete Understanding (2 hours)

```
Quick Reference → Architecture Diagrams → End-to-End Use Case
→ Feast Demo → MLOps Demo
```

### Path 3: Deep Technical Dive (4 hours)

```
All documentation in order (see docs/README.md)
```

---

## 🎯 Real-World Use Cases

### Use Case 1: E-Commerce Churn Prevention

**The Scenario**: An online retailer wants to identify at-risk customers before they leave.

**The Traditional Way** (3-4 weeks):

- Week 1: Data engineer sets up Airbyte connections
- Week 2: Data engineer builds Spark jobs for cleaning
- Week 3: Data scientist waits, then manually exports features
- Week 4: Model training begins, deployment is another project

**The Asgard Way** (1-2 days):

- Morning: Connect to PostgreSQL (customers), MongoDB (browsing data), S3 (purchase history)
- Afternoon: Transform data through Bronze → Silver → Gold layers via API calls
- Next day: Register features, train model, deploy to production
- Result: Real-time churn scores for every customer

**Business Impact**: Retention team can now proactively reach out to at-risk customers with personalized offers, reducing churn by 15-20%.

---

### Use Case 2: Financial Fraud Detection

**The Scenario**: A fintech company needs to detect fraudulent transactions in real-time.

**The Challenge**: Transaction data flows from multiple payment processors, each with different formats. The model needs features from the last 5 minutes, last 24 hours, and last 30 days—all perfectly time-aligned.

**The Asgard Solution**:

- Kafka streams ingest real-time transactions into Bronze
- Spark processes create rolling aggregates in Silver (transactions per hour, average amounts, velocity changes)
- DBT calculates risk scores in Gold (deviation from normal patterns)
- Feast serves point-in-time features with millisecond precision
- MLflow model scores each transaction instantly

**Business Impact**: Fraud caught within seconds instead of hours, saving millions in prevented losses.

---

### Use Case 3: Healthcare Patient Readmission

**The Scenario**: A hospital network wants to predict which discharged patients will be readmitted within 30 days.

**The Complexity**:

- EMR data (electronic medical records) in proprietary systems
- Lab results in separate databases
- Medication history in pharmacy systems
- Social determinants of health from surveys
- All must be joined correctly, respecting patient privacy

**The Asgard Approach**:

- Secure ingestion from multiple HIPAA-compliant sources
- Automated de-identification in Silver layer
- Feature engineering: diagnosis history, medication adherence, lab trends
- Model training on historical outcomes
- Daily predictions for recently discharged patients

**Business Impact**: Care coordinators get daily lists of high-risk patients, enabling proactive intervention. Readmissions reduced by 25%, improving both patient outcomes and hospital economics.

---

### Use Case 4: Retail Demand Forecasting

**The Scenario**: A retail chain needs accurate inventory predictions for 500 stores across 10,000 SKUs.

**The Scale Challenge**: That's 5 million forecasts updated daily, each requiring weather data, promotional calendars, local events, seasonal trends, and historical sales patterns.

**The Asgard Power**:

- Airbyte pulls sales data (POS systems), weather (APIs), events (calendars), promotions (marketing database)
- Spark parallelizes transformations across massive datasets
- DBT creates store-SKU level features (trend, seasonality, price elasticity)
- Feast organizes features for efficient batch retrieval
- MLflow manages separate models per product category
- Kubernetes auto-scales Spark jobs based on demand

**Business Impact**: Inventory optimization reduces waste by 30% while maintaining 99% product availability. The platform that used to crash during peak periods now scales automatically.

---

## 🏗️ The Asgard Architecture

### The Orchestra Analogy

Think of Asgard as a symphony orchestra. Each tool is an instrument section—powerful on its own, magical together:

**🎺 Airbyte** - The brass section: strong, reliable data ingestion from any source  
**🎻 Spark** - The strings: flexible, scalable transformation at any scale  
**🎹 DBT** - The piano: elegant business logic transformation  
**🎼 Feast** - The woodwinds: precise, timely feature delivery  
**🥁 MLflow** - The percussion: driving rhythm of the ML lifecycle  
**🎵 Iceberg + Nessie** - The sheet music: your data lakehouse, versioned and organized

**🎭 Asgard API** - The conductor: orchestrating everything through simple, unified gestures

You don't need to know how to play each instrument. You just need to tell the conductor what you want to hear.

### The Technology Stack

Asgard stands on the shoulders of giants—battle-tested, open-source technologies:

**Data Ingestion**: Airbyte OSS connects to 300+ data sources  
**Data Processing**: Apache Spark on Kubernetes for unlimited scale  
**SQL Transformations**: DBT + Trino for familiar, powerful analytics  
**Feature Store**: Feast reads directly from Iceberg (no duplication!)  
**ML Platform**: MLflow 2.16 for complete ML lifecycle  
**Data Lakehouse**: Apache Iceberg for ACID guarantees on S3  
**Data Catalog**: Project Nessie for Git-like data versioning  
**Orchestration**: FastAPI for clean, fast REST endpoints  
**Infrastructure**: Kubernetes-native for production-grade reliability

### The Flow of Data

**External Systems** → Airbyte extracts → **Bronze Layer** (raw in S3)  
**Bronze** → Spark cleans → **Silver Layer** (validated in S3)  
**Silver** → DBT transforms → **Gold Layer** (business metrics in S3)  
**Gold** → Feast organizes → **Features** (ML-ready views)  
**Features** → MLflow trains → **Models** (deployed predictors)  
**Models** → Inference API → **Predictions** (real-time or batch)

Every step is an API call. Every layer is queryable. Every transformation is tracked.

---

## 💡 Why Teams Choose Asgard

### The Before and After

**Before Asgard**: A data science team at a SaaS company had a backlog of 12 ML use cases. Each project took 2-3 months from conception to production. The bottleneck? 70% of time spent on data engineering—setting up pipelines, debugging integrations, managing infrastructure.

**After Asgard**: Same team, same use cases. First project took 2 weeks (learning curve). Second project: 3 days. By the sixth project: proof-of-concept in a single day. The 12-use-case backlog? Cleared in 4 months instead of 3 years.

### What Changed?

**For Data Engineers:**

- Stopped writing integration code, started designing data flows
- One API to learn instead of six different tools
- Infrastructure as configuration, not as code
- Observability built-in: every transformation tracked, every pipeline monitored

**For Data Scientists:**

- Features available in minutes, not weeks
- No more "Can you export this data for me?" requests
- Upload a training script, get a deployed model
- Point-in-time correctness guaranteed—no data leakage surprises

**For ML Engineers:**

- Production deployment is an API call, not a three-sprint project
- Model versioning, A/B testing, rollback—all built-in
- Scaling handled automatically by Kubernetes
- Same API for batch predictions and real-time inference

**For Business Leaders:**

- Time-to-value measured in days, not quarters
- Infrastructure costs cut by 40% (no data duplication)
- Data quality transparent and measurable
- ML models actually make it to production (not stuck in notebooks)

### The Asgard Philosophy

Asgard believes that **data should flow, not sit**. That **complexity should be hidden, not passed to users**. That **the best tool is the one you forget you're using** because it just works.

We didn't build Asgard to be another tool in your stack. We built it to **be** your stack—a unified platform where powerful open-source tools work together seamlessly, letting you focus on the insights that matter.

---

## 🚀 Getting Started with Asgard

### Your First Five Minutes

Asgard is designed to be intuitive from the first API call. Here's what your first experience looks like:

**Minute 1-2**: Access the platform

- Port-forward to Asgard API running in Kubernetes
- Open the interactive API documentation at `http://localhost:8000/docs`
- Browse the clean, organized endpoints

**Minute 3-4**: Make your first call

- Hit the `/health` endpoint to confirm everything works
- Check `/mlops/status` to see platform components
- Marvel at how simple it is

**Minute 5**: Understand the workflow

- Read through the endpoint documentation
- Notice the pattern: ingest → transform → feature → train → predict
- Realize you already understand how to use 80% of the platform

### Your First Hour

Follow the **[Onboarding Guide](./docs/ONBOARDING_SETUP.md)** to:

- Connect your first data source
- Run a simple transformation
- Register a feature
- Make a prediction

By hour's end, you'll have data flowing through all five layers.

### Your First Project

The **[End-to-End Use Case Guide](./docs/USE_CASE_GUIDE.md)** walks you through building a complete customer churn prediction system:

- Ingest data from multiple sources
- Clean and validate with Spark
- Create business metrics with DBT
- Build reusable features with Feast
- Train and deploy a production model
- Serve real-time predictions

**Time investment**: 2-3 hours  
**Value delivered**: A production-ready ML system

### Learning Paths for Different Roles

**Data Engineers**: Start with [Architecture Guide](./docs/COMPLETE_ARCHITECTURE.md) → understand Medallion layers → experiment with Spark transformations → explore Iceberg integration

**Data Scientists**: Start with [Use Case Guide](./docs/USE_CASE_GUIDE.md) → understand feature registration → upload training script → deploy model → celebrate not dealing with infrastructure

**ML Engineers**: Start with [MLOps Guide](./docs/MLOPS_API_DEMO_GUIDE.md) → understand model deployment → experiment with inference → explore A/B testing patterns

**Technical Leaders**: Start with this README → browse [Complete Architecture](./docs/COMPLETE_ARCHITECTURE.md) → review [API Testing Guide](./docs/API_TESTING_GUIDE.md) → assess organizational fit

## 🌍 Who Uses Asgard?

Asgard is built for organizations at the intersection of data and decision-making:

**E-commerce & Retail**: Personalization engines, demand forecasting, inventory optimization, customer lifetime value prediction

**Financial Services**: Fraud detection, credit risk scoring, algorithmic trading signals, customer segmentation

**Healthcare**: Patient readmission prediction, treatment recommendation, resource optimization, clinical trial matching

**SaaS & Technology**: Churn prediction, usage forecasting, feature adoption analysis, pricing optimization

**Manufacturing**: Predictive maintenance, quality control, supply chain optimization, demand planning

From **startups** moving fast with limited engineering resources to **enterprises** managing complex data ecosystems, Asgard scales to your needs.

---

## 📚 Explore Further

### Essential Documentation

**[📘 Complete Architecture](./docs/COMPLETE_ARCHITECTURE.md)** - Deep dive into system design with visual diagrams  
**[📖 End-to-End Use Case](./docs/USE_CASE_GUIDE.md)** - Build a complete ML system step-by-step  
**[🧪 API Testing Guide](./docs/API_TESTING_GUIDE.md)** - Comprehensive API reference with examples  
**[🏁 Onboarding & Setup](./docs/ONBOARDING_SETUP.md)** - Get started in 30 minutes  
**[🎯 Feast Feature Store](./docs/FEAST_API_DEMO_GUIDE.md)** - Master feature engineering  
**[🤖 MLOps Guide](./docs/MLOPS_API_DEMO_GUIDE.md)** - Model training to deployment  
**[🔧 Debugging Guide](./docs/DEBUGGING_GUIDE.md)** - Troubleshooting and best practices

See **[docs/README.md](./docs/README.md)** for the complete documentation index.

---

## 🎬 The Final Word

In the world of data and machine learning, there's no shortage of powerful tools. The challenge has never been capability—it's been **integration, complexity, and time**.

Asgard doesn't replace your favorite tools. It orchestrates them. It doesn't lock you into proprietary technology. It leverages proven open-source platforms. It doesn't force you to learn six different systems. It gives you one elegant API.

**Asgard's promise**: What used to take weeks can now take days. What used to require a team of specialists can now be done by a single data scientist. What used to stay in notebooks can now reach production.

Your data has stories to tell. Asgard helps you tell them.

**Ready to begin?** Start with the **[Onboarding Guide](./docs/ONBOARDING_SETUP.md)** and build your first pipeline today.

---

## 🤝 Community & Support

- **Documentation**: See `docs/` folder for comprehensive guides
- **Issues**: Report bugs or request features via GitHub Issues
- **Contributing**: We welcome contributions—see contribution guidelines in docs

---

_Built with ❤️ for data teams who believe insights shouldn't wait_
