# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# System deps for some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management (or use pip if preferred)
COPY pyproject.toml ./
# Stub lets setuptools discover the package during dep install without copying source yet.
# The real app/ is copied below and overwrites the stub, preserving layer-cache behaviour.
RUN pip install --no-cache-dir uv && \
    mkdir -p app && touch app/__init__.py && \
    uv pip install --system .

COPY app ./app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
