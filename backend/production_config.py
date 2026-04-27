import os
import boto3
import json
from functools import lru_cache
import logging

# Configure production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_production_config() -> dict:
    """Get production configuration with enhanced security and monitoring."""
    env = os.getenv("ENV", "production")
    
    if env == "production":
        try:
            config = _load_from_secrets_manager("dociq/prod/config")
            logger.info("Loaded production configuration from Secrets Manager")
            return config
        except Exception as e:
            logger.error(f"Failed to load production config: {e}")
            raise Exception("Production configuration unavailable")
    else:
        raise Exception("This module is for production use only")

def _load_from_secrets_manager(secret_name: str) -> dict:
    """Load secrets from AWS Secrets Manager with enhanced error handling."""
    try:
        client = boto3.client("secretsmanager", region_name="us-east-1")
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response["SecretString"])
    except Exception as e:
        logger.error(f"Failed to load secret {secret_name}: {e}")
        raise

def get_database_url() -> str:
    """Get production database URL with connection pooling."""
    config = get_production_config()
    return config["database_url"] + "?sslmode=require"

def get_s3_config() -> dict:
    """Get S3 configuration with production settings."""
    config = get_production_config()
    return {
        "bucket": config["s3_bucket"],
        "region": config["aws_region"],
        "encryption": "AES256",
        "versioning": True
    }

def get_jwt_config() -> dict:
    """Get JWT configuration with production security settings."""
    config = get_production_config()
    return {
        "secret": config["jwt_secret"],
        "expiry_hours": config["jwt_expiry_hours"],
        "algorithm": "HS256"
    }

def get_bedrock_config() -> dict:
    """Get Bedrock configuration with production limits."""
    config = get_production_config()
    return {
        "model_id": config["bedrock_model_id"],
        "max_tokens": 1000,
        "temperature": 0.1,
        "region": config["aws_region"]
    }

def validate_production_config() -> bool:
    """Validate production configuration is complete."""
    try:
        config = get_production_config()
        required_keys = [
            "database_url", "jwt_secret", "s3_bucket", 
            "aws_region", "bedrock_model_id", "env"
        ]
        
        for key in required_keys:
            if key not in config:
                logger.error(f"Missing required config key: {key}")
                return False
        
        # Validate JWT secret length
        if len(config["jwt_secret"]) < 32:
            logger.error("JWT secret must be at least 32 characters")
            return False
        
        logger.info("Production configuration validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        return False
