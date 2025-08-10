# agent_mcp/core/celery_config.py
"""
Celery configuration for the Textile ERP system.
Provides Redis/RabbitMQ broker configuration, task routing, and worker settings.
"""

import os
import ssl
from celery import Celery
from kombu import Queue, Exchange
from celery.schedules import crontab

from .config import logger

# Celery application name
CELERY_APP_NAME = "agent_mcp.textile_erp"

# Broker Configuration
BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Redis SSL Configuration (for production)
REDIS_SSL_CERT_REQS = ssl.CERT_NONE if os.environ.get("REDIS_SSL_CERT_REQS", "none") == "none" else ssl.CERT_REQUIRED
REDIS_SSL_CA_CERTS = os.environ.get("REDIS_SSL_CA_CERTS")
REDIS_SSL_CERTFILE = os.environ.get("REDIS_SSL_CERTFILE")
REDIS_SSL_KEYFILE = os.environ.get("REDIS_SSL_KEYFILE")

# Task Queues Configuration
CELERY_DEFAULT_QUEUE = "default"
CELERY_QUEUES = (
    Queue("default", Exchange("default"), routing_key="default"),
    Queue("high_priority", Exchange("high_priority", type="direct"), routing_key="high_priority"),
    Queue("low_priority", Exchange("low_priority", type="direct"), routing_key="low_priority"),
    Queue("sensor_data", Exchange("sensor_data", type="direct"), routing_key="sensor_data"),
    Queue("production", Exchange("production", type="direct"), routing_key="production"),
    Queue("quality_control", Exchange("quality_control", type="direct"), routing_key="quality_control"),
    Queue("inventory", Exchange("inventory", type="direct"), routing_key="inventory"),
    Queue("maintenance", Exchange("maintenance", type="direct"), routing_key="maintenance"),
    Queue("reports", Exchange("reports", type="direct"), routing_key="reports"),
)

# Task Routing Configuration
CELERY_ROUTES = {
    # High Priority Tasks
    "agent_mcp.tasks.textile_tasks.process_critical_alert": {
        "queue": "high_priority",
        "routing_key": "high_priority",
    },
    "agent_mcp.tasks.textile_tasks.emergency_shutdown_sequence": {
        "queue": "high_priority",
        "routing_key": "high_priority",
    },
    
    # Sensor Data Processing
    "agent_mcp.tasks.textile_tasks.process_sensor_batch": {
        "queue": "sensor_data",
        "routing_key": "sensor_data",
    },
    "agent_mcp.tasks.textile_tasks.aggregate_sensor_data": {
        "queue": "sensor_data",
        "routing_key": "sensor_data",
    },
    
    # Production Tasks
    "agent_mcp.tasks.textile_tasks.optimize_production_schedule": {
        "queue": "production",
        "routing_key": "production",
    },
    "agent_mcp.tasks.textile_tasks.update_production_order": {
        "queue": "production",
        "routing_key": "production",
    },
    
    # Quality Control
    "agent_mcp.tasks.textile_tasks.process_quality_alert": {
        "queue": "quality_control",
        "routing_key": "quality_control",
    },
    "agent_mcp.tasks.textile_tasks.analyze_defect_patterns": {
        "queue": "quality_control",
        "routing_key": "quality_control",
    },
    
    # Inventory Management
    "agent_mcp.tasks.textile_tasks.calculate_reorder_points": {
        "queue": "inventory",
        "routing_key": "inventory",
    },
    "agent_mcp.tasks.textile_tasks.process_inventory_update": {
        "queue": "inventory",
        "routing_key": "inventory",
    },
    
    # Maintenance
    "agent_mcp.tasks.textile_tasks.schedule_maintenance": {
        "queue": "maintenance",
        "routing_key": "maintenance",
    },
    "agent_mcp.tasks.textile_tasks.process_maintenance_alert": {
        "queue": "maintenance",
        "routing_key": "maintenance",
    },
    
    # Report Generation (Low Priority)
    "agent_mcp.tasks.textile_tasks.generate_daily_report": {
        "queue": "reports",
        "routing_key": "reports",
    },
    "agent_mcp.tasks.textile_tasks.generate_monthly_report": {
        "queue": "reports",
        "routing_key": "reports",
    },
    
    # Default low priority for other tasks
    "agent_mcp.tasks.textile_tasks.*": {
        "queue": "low_priority",
        "routing_key": "low_priority",
    },
}

# Worker Configuration
CELERY_WORKER_PREFETCH_MULTIPLIER = int(os.environ.get("CELERY_WORKER_PREFETCH_MULTIPLIER", "1"))
CELERY_WORKER_MAX_TASKS_PER_CHILD = int(os.environ.get("CELERY_WORKER_MAX_TASKS_PER_CHILD", "1000"))
CELERY_WORKER_DISABLE_RATE_LIMITS = os.environ.get("CELERY_WORKER_DISABLE_RATE_LIMITS", "False").lower() == "true"

# Task Configuration
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = os.environ.get("CELERY_TIMEZONE", "UTC")
CELERY_ENABLE_UTC = True

# Task Result Configuration
CELERY_RESULT_EXPIRES = int(os.environ.get("CELERY_RESULT_EXPIRES", "3600"))  # 1 hour
CELERY_TASK_RESULT_EXPIRES = CELERY_RESULT_EXPIRES
CELERY_RESULT_PERSISTENT = True

# Task Retry Configuration
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_REJECT_ON_WORKER_LOST = True

# Rate Limiting
CELERY_TASK_ANNOTATIONS = {
    "agent_mcp.tasks.textile_tasks.process_sensor_batch": {"rate_limit": "100/m"},
    "agent_mcp.tasks.textile_tasks.send_email_notification": {"rate_limit": "10/m"},
    "agent_mcp.tasks.textile_tasks.generate_daily_report": {"rate_limit": "1/h"},
    "agent_mcp.tasks.textile_tasks.backup_database": {"rate_limit": "1/d"},
}

# Periodic Task Schedule (Celery Beat)
CELERY_BEAT_SCHEDULE = {
    # Sensor data aggregation every 5 minutes
    "aggregate-sensor-data-5min": {
        "task": "agent_mcp.tasks.textile_tasks.aggregate_sensor_data",
        "schedule": crontab(minute="*/5"),
        "args": ("5min",),
    },
    
    # Hourly sensor data aggregation
    "aggregate-sensor-data-hourly": {
        "task": "agent_mcp.tasks.textile_tasks.aggregate_sensor_data",
        "schedule": crontab(minute=0),
        "args": ("hourly",),
    },
    
    # Daily production optimization
    "optimize-production-daily": {
        "task": "agent_mcp.tasks.textile_tasks.optimize_production_schedule",
        "schedule": crontab(hour=6, minute=0),  # 6 AM daily
    },
    
    # Calculate reorder points daily
    "calculate-reorder-points": {
        "task": "agent_mcp.tasks.textile_tasks.calculate_reorder_points",
        "schedule": crontab(hour=8, minute=0),  # 8 AM daily
    },
    
    # Quality control analysis twice daily
    "analyze-defect-patterns": {
        "task": "agent_mcp.tasks.textile_tasks.analyze_defect_patterns",
        "schedule": crontab(hour=[9, 21], minute=0),  # 9 AM and 9 PM
    },
    
    # Daily maintenance check
    "check-maintenance-schedule": {
        "task": "agent_mcp.tasks.textile_tasks.check_maintenance_schedule",
        "schedule": crontab(hour=7, minute=30),  # 7:30 AM daily
    },
    
    # Generate daily reports
    "generate-daily-reports": {
        "task": "agent_mcp.tasks.textile_tasks.generate_daily_report",
        "schedule": crontab(hour=23, minute=0),  # 11 PM daily
    },
    
    # Weekly data cleanup
    "cleanup-old-sensor-data": {
        "task": "agent_mcp.tasks.textile_tasks.cleanup_old_sensor_data",
        "schedule": crontab(day_of_week=1, hour=2, minute=0),  # Monday 2 AM
    },
    
    # Monthly reports
    "generate-monthly-reports": {
        "task": "agent_mcp.tasks.textile_tasks.generate_monthly_report",
        "schedule": crontab(day_of_month=1, hour=1, minute=0),  # 1st day of month, 1 AM
    },
    
    # Database backup
    "backup-database": {
        "task": "agent_mcp.tasks.textile_tasks.backup_database",
        "schedule": crontab(hour=3, minute=0),  # 3 AM daily
    },
}

# Monitoring Configuration
CELERY_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True
CELERY_SEND_EVENTS = True

# Security Configuration
CELERY_TASK_ALWAYS_EAGER = os.environ.get("CELERY_TASK_ALWAYS_EAGER", "False").lower() == "true"
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

# Logging Configuration
CELERY_WORKER_HIJACK_ROOT_LOGGER = False
CELERY_WORKER_LOG_FORMAT = "[%(asctime)s: %(levelname)s/%(processName)s] %(message)s"
CELERY_WORKER_TASK_LOG_FORMAT = "[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s"


def create_celery_app() -> Celery:
    """
    Create and configure the Celery application instance.
    
    Returns:
        Celery: Configured Celery application
    """
    # Create Celery app
    app = Celery(CELERY_APP_NAME)
    
    # Update configuration
    app.conf.update(
        broker_url=BROKER_URL,
        result_backend=RESULT_BACKEND,
        task_serializer=CELERY_TASK_SERIALIZER,
        accept_content=CELERY_ACCEPT_CONTENT,
        result_serializer=CELERY_RESULT_SERIALIZER,
        timezone=CELERY_TIMEZONE,
        enable_utc=CELERY_ENABLE_UTC,
        result_expires=CELERY_RESULT_EXPIRES,
        task_routes=CELERY_ROUTES,
        task_default_queue=CELERY_DEFAULT_QUEUE,
        task_queues=CELERY_QUEUES,
        worker_prefetch_multiplier=CELERY_WORKER_PREFETCH_MULTIPLIER,
        worker_max_tasks_per_child=CELERY_WORKER_MAX_TASKS_PER_CHILD,
        worker_disable_rate_limits=CELERY_WORKER_DISABLE_RATE_LIMITS,
        task_acks_late=CELERY_TASK_ACKS_LATE,
        task_reject_on_worker_lost=CELERY_TASK_REJECT_ON_WORKER_LOST,
        task_annotations=CELERY_TASK_ANNOTATIONS,
        beat_schedule=CELERY_BEAT_SCHEDULE,
        send_task_events=CELERY_SEND_TASK_EVENTS,
        task_send_sent_event=CELERY_TASK_SEND_SENT_EVENT,
        send_events=CELERY_SEND_EVENTS,
        task_always_eager=CELERY_TASK_ALWAYS_EAGER,
        eager_propagates_exceptions=CELERY_EAGER_PROPAGATES_EXCEPTIONS,
        worker_hijack_root_logger=CELERY_WORKER_HIJACK_ROOT_LOGGER,
        worker_log_format=CELERY_WORKER_LOG_FORMAT,
        worker_task_log_format=CELERY_WORKER_TASK_LOG_FORMAT,
        result_persistent=CELERY_RESULT_PERSISTENT,
    )
    
    # Redis SSL configuration if needed
    if REDIS_SSL_CA_CERTS or REDIS_SSL_CERTFILE or REDIS_SSL_KEYFILE:
        ssl_config = {
            "ssl_cert_reqs": REDIS_SSL_CERT_REQS,
        }
        if REDIS_SSL_CA_CERTS:
            ssl_config["ssl_ca_certs"] = REDIS_SSL_CA_CERTS
        if REDIS_SSL_CERTFILE:
            ssl_config["ssl_certfile"] = REDIS_SSL_CERTFILE
        if REDIS_SSL_KEYFILE:
            ssl_config["ssl_keyfile"] = REDIS_SSL_KEYFILE
            
        app.conf.update(
            broker_use_ssl=ssl_config,
            redis_backend_use_ssl=ssl_config,
        )
    
    # Autodiscover tasks
    app.autodiscover_tasks(["agent_mcp.tasks"])
    
    logger.info(f"Celery app '{CELERY_APP_NAME}' created successfully")
    logger.info(f"Broker URL: {BROKER_URL}")
    logger.info(f"Result Backend: {RESULT_BACKEND}")
    
    return app


# Global Celery app instance
celery_app = create_celery_app()