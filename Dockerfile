# ==============================================================================
# Stage 1: Build Web Dashboard (React 19 + Vite 8 + Tailwind v4)
# ==============================================================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --prefer-offline --no-audit

COPY index.html tsconfig.json vite.config.ts ./
COPY src/ ./src/

RUN npm run build

# ==============================================================================
# Stage 2: Production Python Runtime (FastAPI + ML Engine + Static Dashboard)
# ==============================================================================
FROM python:3.11-slim AS runner

# Install essential system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python requirements from ble-indoor-positioning
COPY ble-indoor-positioning/requirements.txt ./requirements.txt

# Filter out Windows-only winrt packages for Linux container compatibility
RUN grep -v -i "winrt" requirements.txt > linux_requirements.txt && \
    pip install --no-cache-dir -r linux_requirements.txt

# Copy backend codebase
COPY ble-indoor-positioning/ /app/ble-indoor-positioning/

# Copy compiled Web Dashboard static assets into backend static folder
COPY --from=frontend-builder /app/dist /app/ble-indoor-positioning/server/static

WORKDIR /app/ble-indoor-positioning

# Environment settings
ENV PYTHONUNBUFFERED=1 \
    PORT=8000 \
    HOST=0.0.0.0

EXPOSE 8000

# Healthcheck to verify Location Engine API readiness
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/healthz || exit 1

CMD ["python", "server/app.py"]
