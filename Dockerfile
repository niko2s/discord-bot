FROM python:3.14-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


FROM python:3.14-slim

WORKDIR /app
COPY --from=builder /install /usr/local
COPY bot.py secrets_loader.py ./
COPY cogs ./cogs
COPY utils ./utils

ENV PYTHONUNBUFFERED=1

CMD ["python", "bot.py"]
