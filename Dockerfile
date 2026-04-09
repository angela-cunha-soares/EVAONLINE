# ===========================================
# MULTI-STAGE DOCKERFILE - EVAonline OPTIMIZED
# Uses pyproject.toml as the only source of dependencies
# ===========================================

# ===========================================
# Stage 1: Builder - Production Dependencies
# ===========================================
FROM python:3.12-slim AS builder-prod

# Metadata for improved image traceability
LABEL maintainer="Ângela Cunha Soares <angelasilviane@alumni.usp.br>"
LABEL stage="builder-prod"
LABEL description="Builder stage for production dependencies"

# Configure the working directory for the build
WORKDIR /build

# Copy only the files needed to install dependencies
COPY pyproject.toml ./
COPY requirements.txt ./

# Install build dependencies only for build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*

# Install production dependencies using requirements.txt in an isolated directory
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --target /dependencies -r requirements.txt

# ===========================================
# Stage 1B: Builder - Development Dependencies
# ===========================================
FROM builder-prod AS builder-dev

LABEL stage="builder-dev"

# Install development dependencies from pyproject.toml
# [dev] refers to the project.optional-dependencies section in pyproject.toml
RUN pip install --no-cache-dir --user .[dev]

# ===========================================
# Stage 2: Runtime (Production)
# ===========================================
FROM python:3.12-slim AS runtime

# Final image metadata
LABEL maintainer="Ângela Cunha Soares <angelasilviane@alumni.usp.br>"
LABEL stage="runtime"
LABEL description="Production runtime image for EVAonline"

# Install only essential runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # PostgreSQL runtime
    libpq5 \
    # Geospatial libraries
    libgdal36 \
    libgeos-c1t64 \
    libproj25 \
    # For health checks and scripts
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for security
RUN useradd -m -u 1000 -s /bin/bash evaonline


# Configure Python environment variables for optimization
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app:/dependencies \
    PATH="/dependencies/bin:${PATH}" \
    TZ=America/Sao_Paulo

WORKDIR /app

# Create directories before copying files
RUN mkdir -p /app/logs /app/data /app/temp && \
    chown -R evaonline:evaonline /app

# Copy only production dependencies (does not include dev tools)
COPY --from=builder-prod --chown=evaonline:evaonline /dependencies /dependencies

# Copy code in strategic order for caching
# Files that change little first (better cache)
COPY --chown=evaonline:evaonline pyproject.toml .
COPY --chown=evaonline:evaonline alembic.ini .
COPY --chown=evaonline:evaonline pytest.ini .

# Copy entrypoint (as root to set permissions)
USER root
COPY --chown=root:root docker/backend/entrypoint.sh /entrypoint.sh
COPY --chown=root:root docker/backend/healthcheck.sh /healthcheck.sh
RUN chmod 755 /entrypoint.sh /healthcheck.sh && \
    dos2unix /entrypoint.sh /healthcheck.sh 2>/dev/null || sed -i 's/\r$//' /entrypoint.sh /healthcheck.sh

# Files that change with medium frequency
COPY --chown=evaonline:evaonline config/ ./config/
COPY --chown=evaonline:evaonline alembic/ ./alembic/
COPY --chown=evaonline:evaonline shared_utils/ ./shared_utils/

# Files that change frequently (last - worst cache)
COPY --chown=evaonline:evaonline backend/ ./backend/
COPY --chown=evaonline:evaonline frontend/ ./frontend/

# Switch to non-root user for security.
USER evaonline

# Expose default application port
EXPOSE 8000

# Health check adapted to the service type
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD /healthcheck.sh

# Entrypoint for flexible initialization
ENTRYPOINT ["/entrypoint.sh"]

# Standard command for production
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ===========================================
# Stage 3: Development - Hot Reload e Debug
# ===========================================
FROM runtime AS development

LABEL stage="development"
LABEL description="Development image com hot-reload"

# Copy development dependencies overwriting production
COPY --from=builder-dev --chown=evaonline:evaonline /dependencies-dev /dependencies

USER evaonline

# Environment variables for development
ENV RELOAD=true \
    ENVIRONMENT=development \
    LOG_LEVEL=DEBUG \
    PYTHONPATH=/app:/dependencies

# Standard command for development with hot-reload
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ===========================================
# Stage 4: Testing - Testing Environment
# ===========================================
FROM development AS testing

LABEL stage="testing"
LABEL description="Testing image com pytest"

# Install additional tools for testing
USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

USER evaonline

# Copy tests
COPY --chown=evaonline:evaonline backend/tests/ ./backend/tests/

# Copy test entrypoint
COPY --chown=evaonline:evaonline docker/docker-entrypoint-tests.sh /entrypoint-tests.sh
RUN chmod +x /entrypoint-tests.sh

# Environment variables for testing
ENV ENVIRONMENT=testing \
    TESTING=true

# Entrypoint for test execution
ENTRYPOINT ["/entrypoint-tests.sh"]

# Fallback for direct test execution
CMD ["pytest", "-v", "--tb=short", "--color=yes"]
