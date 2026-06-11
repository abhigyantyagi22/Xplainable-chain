# ── Stage 1: build dependencies ───────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Pre-install CPU-only PyTorch before everything else.
# Without this, pgmpy / dowhy / causal-learn pull in the full CUDA variant
# (~2 GB of NVIDIA libraries) which blows past the 512 MB free-tier limit.
RUN pip install --no-cache-dir --user \
    torch \
    --index-url https://download.pytorch.org/whl/cpu

# Install the rest of the dependencies (torch is already satisfied, so
# downstream packages won't try to upgrade to the CUDA build).
RUN pip install --no-cache-dir --user -r requirements.txt


# ── Stage 2: runtime ───────────────────────────────────────────────────────────
FROM python:3.12-slim

RUN apt-get update && \
    apt-get upgrade -y && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 appuser

WORKDIR /app

COPY --from=builder /root/.local /home/appuser/.local

COPY --chown=appuser:appuser . .

USER appuser

ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Longer start period — causal/ML libraries are slow to import on first boot.
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" \
    || exit 1

# Single worker keeps RSS under 512 MB on Render's free tier.
# Uvicorn is async so concurrency is still handled without multiple processes.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
