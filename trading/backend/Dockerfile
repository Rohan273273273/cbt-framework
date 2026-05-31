FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev curl python3-dev git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Upgrade pip first
RUN pip install --upgrade pip

# Install packages one group at a time so failures are obvious
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" websockets python-multipart httpx
RUN pip install --no-cache-dir alpaca-py
RUN pip install --no-cache-dir psycopg2-binary asyncpg redis neo4j
RUN pip install --no-cache-dir polars pandas numpy
RUN pip install --no-cache-dir lightgbm scikit-learn joblib river
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir transformers sentencepiece
RUN pip install --no-cache-dir ccxt yfinance fredapi
RUN pip install --no-cache-dir feedparser || pip install --no-cache-dir "feedparser==6.0.8"
RUN pip install --no-cache-dir "langgraph==0.2.28" "langchain-core==0.3.8"
RUN pip install --no-cache-dir apscheduler pydantic-settings python-dotenv
RUN pip install --no-cache-dir tqdm aiohttp tenacity ta

# Pre-download FinBERT model at build time
RUN python -c "\
from transformers import AutoTokenizer, AutoModelForSequenceClassification; \
AutoTokenizer.from_pretrained('ProsusAI/finbert'); \
AutoModelForSequenceClassification.from_pretrained('ProsusAI/finbert')" \
    || echo "FinBERT will download on first run"

COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
