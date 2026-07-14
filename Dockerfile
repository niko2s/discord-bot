FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


FROM python:3.12-slim

ARG GIT_SHA=unknown
ARG REPOSITORY_URL=unknown

WORKDIR /app
COPY --from=builder /install /usr/local
COPY bot.py secrets_loader.py ./
COPY cogs ./cogs
COPY utils ./utils

ENV PYTHONUNBUFFERED=1 \
    BOT_GIT_SHA=${GIT_SHA} \
    BOT_REPOSITORY_URL=${REPOSITORY_URL}

LABEL org.opencontainers.image.revision=${GIT_SHA} \
      org.opencontainers.image.source=${REPOSITORY_URL}

CMD ["python", "bot.py"]
