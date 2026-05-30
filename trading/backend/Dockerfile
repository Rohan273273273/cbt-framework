FROM python:3.11-slim

WORKDIR /app

# System dependencies for numba, psycopg2, torch, feedparser
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev curl python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install sgmllib3k (feedparser dep) from source before feedparser
RUN pip install --no-cache-dir sgmllib3k --no-build-isolation || true

RUN pip install --no-cache-dir -r requirements.txt

# Pre-download FinBERT model at build time (avoids runtime download)
RUN python -c "\
from transformers import AutoTokenizer, AutoModelForSequenceClassification; \
AutoTokenizer.from_pretrained('ProsusAI/finbert'); \
AutoModelForSequenceClassification.from_pretrained('ProsusAI/finbert')" \
    || echo "FinBERT download failed — will retry at runtime"

COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
