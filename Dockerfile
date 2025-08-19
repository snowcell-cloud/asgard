FROM python:3.10-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Create non-root user
RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

# Copy uv files
COPY pyproject.toml uv.lock ./
COPY app/ ./app/

# Install dependencies with uv
RUN uv sync --frozen --no-cache

# Change ownership to app user
RUN chown -R app:app /app
USER app

EXPOSE 8000

# Use uv to run the application
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
