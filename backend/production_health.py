import time
import psutil
import boto3
from sqlalchemy import text
from database import SessionLocal, engine
from config import get_config
import logging

logger = logging.getLogger(__name__)

class ProductionHealthChecker:
    """Production health monitoring and diagnostics."""
    
    def __init__(self):
        self.config = get_config()
        self.health_status = {
            "timestamp": None,
            "status": "unhealthy",
            "checks": {}
        }
    
    def check_database_health(self) -> dict:
        """Check database connectivity and performance."""
        try:
            start_time = time.time()
            
            # Test basic connectivity
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                connection_time = time.time() - start_time
            
            # Check table counts
            with SessionLocal() as db:
                companies = db.execute(text("SELECT COUNT(*) FROM companies")).scalar()
                users = db.execute(text("SELECT COUNT(*) FROM users")).scalar()
                documents = db.execute(text("SELECT COUNT(*) FROM documents")).scalar()
                chunks = db.execute(text("SELECT COUNT(*) FROM document_chunks")).scalar()
            
            return {
                "status": "healthy",
                "connection_time_ms": round(connection_time * 1000, 2),
                "tables": {
                    "companies": companies,
                    "users": users,
                    "documents": documents,
                    "chunks": chunks
                }
            }
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def check_s3_health(self) -> dict:
        """Check S3 connectivity and bucket status."""
        try:
            import boto3
            from config import get_config
            
            config = get_config()
            s3_client = boto3.client("s3", region_name=config["aws_region"])
            
            start_time = time.time()
            
            # Test bucket access
            response = s3_client.head_bucket(Bucket=config["s3_bucket"])
            bucket_time = time.time() - start_time
            
            # Get bucket size (approximate)
            objects = s3_client.list_objects_v2(Bucket=config["s3_bucket"], MaxKeys=1)
            
            return {
                "status": "healthy",
                "bucket": config["s3_bucket"],
                "access_time_ms": round(bucket_time * 1000, 2),
                "object_count": response.get('KeyCount', 0)
            }
            
        except Exception as e:
            logger.error(f"S3 health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def check_bedrock_health(self) -> dict:
        """Check AWS Bedrock availability."""
        try:
            import boto3
            from config import get_config
            
            config = get_config()
            bedrock = boto3.client("bedrockruntime", region_name=config["aws_region"])
            
            # Test model availability
            response = bedrock.list_foundation_models()
            model_available = any(
                model['modelId'] == config["bedrock_model_id"] 
                for model in response['modelSummaries']
            )
            
            return {
                "status": "healthy" if model_available else "unhealthy",
                "model": config["bedrock_model_id"],
                "available": model_available
            }
            
        except Exception as e:
            logger.error(f"Bedrock health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def check_system_health(self) -> dict:
        """Check system resources."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "status": "healthy",
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_percent": disk.percent,
                "disk_free_gb": round(disk.free / (1024**3), 2)
            }
            
        except Exception as e:
            logger.error(f"System health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def run_health_checks(self) -> dict:
        """Run all health checks and return comprehensive status."""
        self.health_status["timestamp"] = time.time()
        
        # Run all checks
        self.health_status["checks"]["database"] = self.check_database_health()
        self.health_status["checks"]["s3"] = self.check_s3_health()
        self.health_status["checks"]["bedrock"] = self.check_bedrock_health()
        self.health_status["checks"]["system"] = self.check_system_health()
        
        # Determine overall status
        all_healthy = all(
            check["status"] == "healthy" 
            for check in self.health_status["checks"].values()
        )
        
        self.health_status["status"] = "healthy" if all_healthy else "unhealthy"
        
        return self.health_status
    
    def get_health_metrics(self) -> dict:
        """Get detailed health metrics for monitoring."""
        health = self.run_health_checks()
        
        # Add additional metrics
        health["uptime"] = time.time() - psutil.boot_time()
        health["load_average"] = psutil.getloadavg()
        
        return health

# FastAPI health endpoint integration
def get_production_health() -> dict:
    """Get production health status for FastAPI endpoint."""
    checker = ProductionHealthChecker()
    return checker.run_health_checks()

# Individual check functions for detailed monitoring
def check_database_only() -> dict:
    """Check database health only."""
    checker = ProductionHealthChecker()
    return checker.check_database_health()

def check_s3_only() -> dict:
    """Check S3 health only."""
    checker = ProductionHealthChecker()
    return checker.check_s3_health()

def check_bedrock_only() -> dict:
    """Check Bedrock health only."""
    checker = ProductionHealthChecker()
    return checker.check_bedrock_health()

def check_system_only() -> dict:
    """Check system health only."""
    checker = ProductionHealthChecker()
    return checker.check_system_health()
