FROM python:3.10-slim AS builder

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
FROM python:3.10-slim AS production

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy uv files and README
COPY pyproject.toml uv.lock README.md ./
COPY app/ ./app/

# Set environment variable to install in system Python
ENV UV_SYSTEM_PYTHON=1

# Install dependencies with uv sync (production only) as root first
RUN uv sync --frozen --no-dev

# Create non-root user and change ownership
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app

# Switch to app user
USER app

EXPOSE 8000

# Use uv to run uvicorn (this ensures the right environment)
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
