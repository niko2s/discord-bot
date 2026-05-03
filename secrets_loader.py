"""
Pulls runtime secrets from AWS Secrets Manager into os.environ at startup.

Activated by setting BOT_SECRET_ID in the environment. Skipped silently when
unset, so local dev keeps using `.env` without any AWS dependency.

The secret value must be a JSON object mapping env-var names to string values,
e.g. {"DISCORD_TOKEN": "...", "OPENAI_API_KEY": "...", "URBAN_KEY": "..."}.
Already-set env vars win, so explicit container env always overrides AWS.
"""
import json
import logging
import os


def load_secret_from_aws() -> None:
    secret_id = os.environ.get("BOT_SECRET_ID")
    if not secret_id:
        return

    try:
        import boto3
    except ImportError:
        logging.warning("BOT_SECRET_ID set but boto3 not installed; skipping AWS fetch")
        return

    region = os.environ.get("AWS_REGION", "eu-central-1")
    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_id)
    secret = json.loads(response["SecretString"])

    for key, value in secret.items():
        if key in os.environ:
            continue
        os.environ[key] = str(value)

    logging.info("Loaded %d keys from AWS Secrets Manager (%s)", len(secret), secret_id)
