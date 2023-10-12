FROM amd64/python:3.11-slim-buster 

WORKDIR /app

COPY . /app

RUN apt-get update && \
    apt-get install -y build-essential && \
    pip install --no-cache-dir -r requirements.txt

CMD ["python", "bot.py"]