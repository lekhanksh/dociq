import time
import json
import boto3
from datetime import datetime, timedelta
from sqlalchemy import text
from database import SessionLocal
from models import QueryLog, ActivityLog
import logging

logger = logging.getLogger(__name__)

class ProductionMonitor:
    """Production monitoring and metrics collection."""
    
    def __init__(self):
        self.cloudwatch = boto3.client("cloudwatch", region_name="us-east-1")
        self.logs = boto3.client("logs", region_name="us-east-1")
    
    def put_custom_metric(self, namespace, metric_name, value, unit="Count", dimensions=None):
        """Put custom metric to CloudWatch."""
        try:
            metric_data = {
                "Namespace": namespace,
                "MetricData": [
                    {
                        "MetricName": metric_name,
                        "Timestamp": datetime.utcnow(),
                        "Value": value,
                        "Unit": unit
                    }
                ]
            }
            
            if dimensions:
                metric_data["MetricData"][0]["Dimensions"] = dimensions
            
            self.cloudwatch.put_metric_data(**metric_data)
            logger.info(f"Metric sent: {namespace}/{metric_name} = {value}")
            
        except Exception as e:
            logger.error(f"Failed to send metric {namespace}/{metric_name}: {e}")
    
    def track_query_performance(self, query_time_ms, chunks_used, success=True):
        """Track query performance metrics."""
        # Query response time
        self.put_custom_metric(
            "DocIQ/Application",
            "QueryResponseTime",
            query_time_ms,
            "Milliseconds",
            [{"Name": "Success", "Value": "true" if success else "false"}]
        )
        
        # Chunks used
        self.put_custom_metric(
            "DocIQ/Application",
            "ChunksUsed",
            chunks_used,
            "Count"
        )
        
        # Query count
        self.put_custom_metric(
            "DocIQ/Application",
            "QueryCount",
            1,
            "Count",
            [{"Name": "Success", "Value": "true" if success else "false"}]
        )
    
    def track_upload_performance(self, file_size_bytes, processing_time_ms, success=True):
        """Track document upload metrics."""
        # Upload response time
        self.put_custom_metric(
            "DocIQ/Application",
            "UploadResponseTime",
            processing_time_ms,
            "Milliseconds",
            [{"Name": "Success", "Value": "true" if success else "false"}]
        )
        
        # File size
        self.put_custom_metric(
            "DocIQ/Application",
            "UploadFileSize",
            file_size_bytes,
            "Bytes"
        )
        
        # Upload count
        self.put_custom_metric(
            "DocIQ/Application",
            "UploadCount",
            1,
            "Count",
            [{"Name": "Success", "Value": "true" if success else "false"}]
        )
    
    def track_user_activity(self, action, user_id=None):
        """Track user activity metrics."""
        self.put_custom_metric(
            "DocIQ/Application",
            "UserActivity",
            1,
            "Count",
            [
                {"Name": "Action", "Value": action},
                {"Name": "Anonymous", "Value": "false" if user_id else "true"}
            ]
        )
    
    def track_database_metrics(self):
        """Track database performance metrics."""
        try:
            with SessionLocal() as db:
                # Active connections
                connections = db.execute(text("""
                    SELECT count(*) 
                    FROM pg_stat_activity 
                    WHERE state = 'active'
                """)).scalar()
                
                # Database size
                db_size = db.execute(text("""
                    SELECT pg_size_pretty(pg_database_size(current_database()))
                """)).scalar()
                
                # Table sizes
                table_sizes = db.execute(text("""
                    SELECT 
                        schemaname,
                        tablename,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                """)).fetchall()
                
                # Send metrics
                self.put_custom_metric(
                    "DocIQ/Database",
                    "ActiveConnections",
                    connections,
                    "Count"
                )
                
                # Log table sizes
                for row in table_sizes:
                    self.put_custom_metric(
                        "DocIQ/Database",
                        "TableSize",
                        1,  # We'll log this as a count
                        "Count",
                        [
                            {"Name": "Table", "Value": row.tablename},
                            {"Name": "Schema", "Value": row.schemaname}
                        ]
                    )
                
                logger.info(f"Database metrics: connections={connections}, size={db_size}")
                
        except Exception as e:
            logger.error(f"Failed to collect database metrics: {e}")
    
    def track_system_metrics(self):
        """Track system performance metrics."""
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.put_custom_metric(
                "DocIQ/System",
                "CPUUtilization",
                cpu_percent,
                "Percent"
            )
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.put_custom_metric(
                "DocIQ/System",
                "MemoryUtilization",
                memory.percent,
                "Percent"
            )
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.put_custom_metric(
                "DocIQ/System",
                "DiskUtilization",
                disk_percent,
                "Percent"
            )
            
            # Network I/O
            network = psutil.net_io_counters()
            if network:
                self.put_custom_metric(
                    "DocIQ/System",
                    "NetworkBytesIn",
                    network.bytes_recv,
                    "Bytes"
                )
                self.put_custom_metric(
                    "DocIQ/System",
                    "NetworkBytesOut",
                    network.bytes_sent,
                    "Bytes"
                )
            
            logger.info(f"System metrics: CPU={cpu_percent}%, Memory={memory.percent}%, Disk={disk_percent}%")
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
    
    def create_cloudwatch_log_group(self, log_group_name):
        """Create CloudWatch log group if it doesn't exist."""
        try:
            self.logs.create_log_group(logGroupName=log_group_name)
            logger.info(f"Created log group: {log_group_name}")
        except self.logs.exceptions.ResourceAlreadyExistsException:
            # Log group already exists
            pass
        except Exception as e:
            logger.error(f"Failed to create log group {log_group_name}: {e}")
    
    def send_log_to_cloudwatch(self, log_group, log_stream, message, level="INFO"):
        """Send log message to CloudWatch."""
        try:
            timestamp = int(time.time() * 1000)
            
            log_event = {
                "timestamp": timestamp,
                "message": f"[{level}] {message}"
            }
            
            self.logs.put_log_events(
                logGroupName=log_group,
                logStreamName=log_stream,
                logEvents=[log_event]
            )
            
        except Exception as e:
            logger.error(f"Failed to send log to CloudWatch: {e}")
    
    def setup_monitoring(self):
        """Set up monitoring infrastructure."""
        # Create log groups
        self.create_cloudwatch_log_group("/aws/ec2/dociq")
        self.create_cloudwatch_log_group("/aws/application/dociq")
        self.create_cloudwatch_log_group("/aws/database/dociq")
        
        logger.info("Monitoring infrastructure setup complete")
    
    def generate_health_report(self) -> dict:
        """Generate comprehensive health report."""
        try:
            # Get recent metrics
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=1)
            
            # Get application metrics
            app_metrics = self.cloudwatch.get_metric_statistics(
                Namespace="DocIQ/Application",
                MetricName="QueryResponseTime",
                StartTime=start_time,
                EndTime=end_time,
                Period=300,  # 5-minute intervals
                Statistics=["Average", "Maximum", "Minimum"]
            )
            
            # Get system metrics
            system_metrics = self.cloudwatch.get_metric_statistics(
                Namespace="DocIQ/System",
                MetricName="CPUUtilization",
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=["Average", "Maximum"]
            )
            
            # Get database metrics
            db_metrics = self.cloudwatch.get_metric_statistics(
                Namespace="DocIQ/Database",
                MetricName="ActiveConnections",
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=["Average", "Maximum"]
            )
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "application": {
                    "query_response_time": self._extract_metric_value(app_metrics, "Average"),
                    "query_response_time_max": self._extract_metric_value(app_metrics, "Maximum")
                },
                "system": {
                    "cpu_avg": self._extract_metric_value(system_metrics, "Average"),
                    "cpu_max": self._extract_metric_value(system_metrics, "Maximum")
                },
                "database": {
                    "active_connections_avg": self._extract_metric_value(db_metrics, "Average"),
                    "active_connections_max": self._extract_metric_value(db_metrics, "Maximum")
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to generate health report: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
    
    def _extract_metric_value(self, metrics_response, statistic):
        """Extract specific statistic value from CloudWatch response."""
        try:
            datapoints = metrics_response.get('Datapoints', [])
            if datapoints:
                # Get the most recent datapoint
                latest = max(datapoints, key=lambda x: x['Timestamp'])
                return latest.get(statistic, 0)
            return 0
        except Exception:
            return 0

# Global monitor instance
monitor = ProductionMonitor()

# Decorator for tracking query performance
def track_query_metrics(func):
    """Decorator to track query performance metrics."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            query_time = (time.time() - start_time) * 1000
            
            # Extract chunks_used if available
            chunks_used = 0
            if isinstance(result, dict) and 'chunks_used' in result:
                chunks_used = result['chunks_used']
            
            monitor.track_query_performance(query_time, chunks_used, success=True)
            return result
            
        except Exception as e:
            query_time = (time.time() - start_time) * 1000
            monitor.track_query_performance(query_time, 0, success=False)
            raise
    
    return wrapper

# Decorator for tracking upload performance
def track_upload_metrics(func):
    """Decorator to track upload performance metrics."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            upload_time = (time.time() - start_time) * 1000
            
            # Extract file size if available
            file_size = 0
            if 'file' in kwargs:
                file_size = kwargs['file'].size if hasattr(kwargs['file'], 'size') else 0
            
            monitor.track_upload_performance(file_size, upload_time, success=True)
            return result
            
        except Exception as e:
            upload_time = (time.time() - start_time) * 1000
            monitor.track_upload_performance(0, upload_time, success=False)
            raise
    
    return wrapper
