import os
import boto3
import json
from functools import lru_cache

@lru_cache(maxsize=1)
def get_config() -> dict:
    env = os.getenv("ENV", "development")

    if env == "production":
        return _load_from_secrets_manager("dociq/prod/config")
    elif env == "staging":
        return _load_from_secrets_manager("dociq/staging/config")
    elif env == "demo":
        return _load_from_secrets_manager("dociq/demo/config")
    else:
        # Local dev: read from environment variables
        return {
            "database_url": os.getenv("DATABASE_URL"),
            "jwt_secret": os.getenv("JWT_SECRET"),
            "jwt_expiry_hours": int(os.getenv("JWT_EXPIRY_HOURS", "24")),
            "s3_bucket": os.getenv("S3_BUCKET_NAME"),
            "aws_region": os.getenv("AWS_REGION", "us-east-1"),
            "bedrock_model_id": os.getenv("BEDROCK_MODEL_ID"),
            "env": env,
        }

def _load_from_secrets_manager(secret_name: str) -> dict:
    client = boto3.client("secretsmanager", region_name="us-east-1")
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response["SecretString"])
