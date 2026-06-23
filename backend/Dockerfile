FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DEFAULT_TIMEOUT=300
ENV DATABASE_URL=sqlite:////app/smartloan_ai.db
ENV SMARTLOAN_CUSTOMER_DB_PATH=/app/smartloan_customer_portal.db
ENV SMARTLOAN_RAG_DB_PATH=/app/smartloan_ai_rag.db

RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN python -m pip install --upgrade pip setuptools wheel && pip install --prefer-binary --retries 20 --default-timeout=300 -r requirements.txt

COPY app ./app

RUN mkdir -p /app/storage /app/uploads /app/data /app/storage/pdfs /app/storage/generated_pdfs /app/storage/documents

EXPOSE 20000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "20000"]
