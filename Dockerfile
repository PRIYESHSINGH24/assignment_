FROM python:3.14-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install a pinned version of uv
COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /uvx /bin/

# Configure uv
ENV UV_COMPILE_BYTECODE=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create non-root user
RUN useradd --create-home --uid 1000 django

COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev --no-install-project

# Copy application
COPY --chown=django:django . .

USER django

EXPOSE 8000

# Development server
CMD ["sh", "-c", "uv run python manage.py migrate && exec uv run python manage.py runserver 0.0.0.0:8000"]