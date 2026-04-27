import os
import boto3
import json
from functools import lru_cache
import logging

# Configure demo logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_demo_config() -> dict:
    """Get demo configuration optimized for free tier usage."""
    env = os.getenv("ENV", "demo")
    
    if env == "demo":
        try:
            config = _load_from_secrets_manager("dociq/demo/config")
            logger.info("Loaded demo configuration from Secrets Manager")
            return config
        except Exception as e:
            logger.error(f"Failed to load demo config: {e}")
            # Fallback to environment variables for local demo
            return _get_demo_fallback_config()
    else:
        raise Exception("This module is for demo use only")

def _load_from_secrets_manager(secret_name: str) -> dict:
    """Load secrets from AWS Secrets Manager."""
    try:
        client = boto3.client("secretsmanager", region_name="us-east-1")
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response["SecretString"])
    except Exception as e:
        logger.error(f"Failed to load secret {secret_name}: {e}")
        raise

def _get_demo_fallback_config() -> dict:
    """Fallback configuration for local demo development."""
    return {
        "database_url": os.getenv("DATABASE_URL", "postgresql://dociq:localpassword@localhost:5432/dociq_demo"),
        "jwt_secret": os.getenv("JWT_SECRET", "demo-secret-minimum-32-characters-long"),
        "jwt_expiry_hours": int(os.getenv("JWT_EXPIRY_HOURS", "24")),
        "s3_bucket": os.getenv("S3_BUCKET_NAME", "dociq-demo-documents"),
        "aws_region": os.getenv("AWS_REGION", "us-east-1"),
        "bedrock_model_id": os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"),
        "env": "demo",
        "demo_mode": True,
        "cost_optimization": {
            "free_tier": True,
            "single_instance": True,
            "no_alb": True,
            "no_cloudfront": True,
            "single_az": True
        }
    }

def get_database_config() -> dict:
    """Get database configuration optimized for demo."""
    config = get_demo_config()
    return {
        "url": config["database_url"],
        "pool_size": 3,  # Reduced for free tier
        "max_overflow": 5,
        "pool_recycle": 3600,
        "echo": False
    }

def get_s3_config() -> dict:
    """Get S3 configuration for demo."""
    config = get_demo_config()
    return {
        "bucket": config["s3_bucket"],
        "region": config["aws_region"],
        "encryption": "AES256",
        "versioning": False,  # Disable to save cost
        "lifecycle": False  # Disable to save cost
    }

def get_jwt_config() -> dict:
    """Get JWT configuration for demo."""
    config = get_demo_config()
    return {
        "secret": config["jwt_secret"],
        "expiry_hours": config["jwt_expiry_hours"],
        "algorithm": "HS256"
    }

def get_bedrock_config() -> dict:
    """Get Bedrock configuration with demo limits."""
    config = get_demo_config()
    return {
        "model_id": config["bedrock_model_id"],
        "max_tokens": 500,  # Reduced for demo
        "temperature": 0.1,
        "region": config["aws_region"],
        "rate_limit": 10  # Requests per minute
    }

def get_demo_limits() -> dict:
    """Get demo-specific limits and warnings."""
    return {
        "max_file_size": 5 * 1024 * 1024,  # 5MB (reduced from 10MB)
        "max_concurrent_queries": 5,  # Reduced for demo
        "max_documents_per_company": 50,  # Limited for demo
        "rate_limit_per_minute": 10,
        "free_tier_warnings": [
            "EC2 t2.micro limited to 750 hours/month",
            "RDS t3.micro limited to 750 hours/month",
            "Single instance - no load balancing",
            "Single AZ - no high availability"
        ]
    }

def validate_demo_config() -> bool:
    """Validate demo configuration."""
    try:
        config = get_demo_config()
        required_keys = [
            "database_url", "jwt_secret", "s3_bucket", 
            "aws_region", "bedrock_model_id", "env"
        ]
        
        for key in required_keys:
            if key not in config:
                logger.error(f"Missing required config key: {key}")
                return False
        
        # Check demo-specific settings
        if config.get("env") != "demo":
            logger.error("Configuration not in demo mode")
            return False
        
        logger.info("Demo configuration validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Demo configuration validation failed: {e}")
        return False

def get_cost_monitoring_config() -> dict:
    """Get cost monitoring configuration for demo."""
    return {
        "budget_limit": 20.0,  # $20/month limit
        "alert_threshold": 15.0,  # Alert at $15
        "monitoring_interval": 3600,  # Check every hour
        "free_tier_tracking": True,
        "cost_optimization_tips": [
            "Monitor EC2 hours to stay within free tier",
            "Keep RDS storage under 20GB",
            "Limit S3 usage to minimum",
            "Use CloudWatch free tier (10 metrics)"
        ]
    }
