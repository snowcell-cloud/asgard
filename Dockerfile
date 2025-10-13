FROM python:3.11-slim AS builder

# Install build dependencies for packages that need compilation
# Including Apache Arrow development libraries for pyarrow
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    cmake \
    libarrow-dev \
    libparquet-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy uv files and README
COPY pyproject.toml uv.lock README.md ./
COPY app/ ./app/

# Set environment variable to install in system Python
ENV UV_SYSTEM_PYTHON=1

# Install all dependencies including dev (for testing)
RUN uv sync --frozen

# Run tests
RUN uv run pytest

# Production stage
FROM python:3.11-slim AS production

# Install build dependencies for packages that need compilation
# Including Apache Arrow development libraries for pyarrow
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    cmake \
    libarrow-dev \
    libparquet-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Create non-root user first
RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

# Copy uv files and README
COPY pyproject.toml uv.lock README.md ./
COPY app/ ./app/

# Change ownership to app user before installing
RUN chown -R app:app /app

# Create writable temp directory for dbt projects
RUN mkdir -p /tmp/dbt_projects && chown app:app /tmp/dbt_projects

# Create writable directories for Feast and ML models
RUN mkdir -p /tmp/feast_repo /tmp/models && chown app:app /tmp/feast_repo /tmp/models

# Switch to app user
USER app

# Set environment variables
ENV UV_SYSTEM_PYTHON=1
ENV DBT_PROJECT_DIR=/tmp/dbt_projects
ENV TMPDIR=/tmp
ENV FEAST_REPO_PATH=/tmp/feast_repo
ENV MODEL_STORAGE_PATH=/tmp/models
# Install dependencies with uv sync (production only)
RUN uv sync --frozen --no-dev

EXPOSE 8000

# Use uv to run uvicorn (this ensures the right environment)
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]