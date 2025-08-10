# Celery Task Queue Setup for Textile ERP System

This document provides comprehensive setup instructions for the Celery task queue integration in the Agent-MCP textile ERP system.

## Overview

The Celery integration provides:
- Background task processing for sensor data, production scheduling, quality control, inventory management, maintenance, and reporting
- Periodic task scheduling with Celery Beat
- Multiple queues for task prioritization
- Comprehensive monitoring and management APIs
- Production-ready worker management scripts

## Prerequisites

### Required Services

1. **Redis** (recommended) or **RabbitMQ** as message broker
2. **Python 3.10+** with the updated dependencies

### Installing Redis (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

### Installing Redis (macOS with Homebrew)
```bash
brew install redis
brew services start redis
```

### Installing RabbitMQ (Alternative)
```bash
# Ubuntu/Debian
sudo apt install rabbitmq-server
sudo systemctl start rabbitmq-server
sudo systemctl enable rabbitmq-server

# macOS
brew install rabbitmq
brew services start rabbitmq
```

## Configuration

### Environment Variables

Create a `.env` file in the project root or set environment variables:

```bash
# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
CELERY_TIMEZONE=UTC

# Worker Configuration
CELERY_WORKER_PREFETCH_MULTIPLIER=1
CELERY_WORKER_MAX_TASKS_PER_CHILD=1000

# Optional: Redis SSL (for production)
REDIS_SSL_CERT_REQS=none
REDIS_SSL_CA_CERTS=/path/to/ca-certificates.crt
REDIS_SSL_CERTFILE=/path/to/client.crt
REDIS_SSL_KEYFILE=/path/to/client.key

# Monitoring
FLOWER_PORT=5555
```

### Production Configuration

For production deployments, consider:

1. **Redis Configuration** (`/etc/redis/redis.conf`):
```
# Memory management
maxmemory 2gb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000

# Security
requirepass your_redis_password
bind 127.0.0.1

# Performance
tcp-keepalive 300
timeout 300
```

2. **SSL/TLS Configuration**:
```bash
# Set SSL environment variables
export REDIS_SSL_CERT_REQS=required
export REDIS_SSL_CA_CERTS=/etc/ssl/certs/ca-certificates.crt
export CELERY_BROKER_URL=rediss://username:password@hostname:6380/0
```

## Installation

1. **Install Dependencies**:
```bash
pip install -r requirements.txt
# Or if using uv:
uv pip install -r requirements.txt
```

2. **Verify Installation**:
```bash
celery --version
```

## Starting the System

### Option 1: Quick Start (All Components)

```bash
# Make sure Redis is running
sudo systemctl start redis

# Start all workers using the convenience script
./start_workers.sh start
```

### Option 2: Manual Component Start

1. **Start Individual Workers**:
```bash
# High-priority worker (sensor data, critical alerts)
python start_celery_worker.py --high-priority

# Production worker (production, quality control)
python start_celery_worker.py --production

# Maintenance worker (maintenance, inventory)
python start_celery_worker.py --maintenance

# Reports worker (reports, low priority tasks)
python start_celery_worker.py --reports
```

2. **Start Celery Beat Scheduler**:
```bash
python start_celery_worker.py beat
```

3. **Start Flower Monitoring** (optional):
```bash
python start_celery_worker.py flower --flower-port 5555
```

### Option 3: Custom Worker Configuration

```bash
# Custom worker with specific queues
python start_celery_worker.py worker \
  --queues high_priority,sensor_data \
  --concurrency 4 \
  --worker-name critical_worker \
  --max-tasks-per-child 500

# Worker with specific parameters
python start_celery_worker.py worker \
  --queues production,quality_control \
  --concurrency 2 \
  --log-level DEBUG \
  --max-memory-per-child 204800  # 200MB
```

## Task Queues and Routing

The system uses the following queues:

| Queue | Purpose | Priority | Workers |
|-------|---------|----------|---------|
| `high_priority` | Critical alerts, emergency tasks | Critical | 4 concurrent |
| `sensor_data` | Sensor data processing | High | Shared with high_priority |
| `production` | Production scheduling | Normal | 2 concurrent |
| `quality_control` | Quality analysis | Normal | Shared with production |
| `inventory` | Inventory management | Normal | 2 concurrent |
| `maintenance` | Maintenance scheduling | Normal | Shared with inventory |
| `reports` | Report generation | Low | 1 concurrent |
| `low_priority` | Background cleanup | Low | Shared with reports |
| `default` | General tasks | Normal | 2 concurrent |

## Monitoring and Management

### Web Interface (Flower)

Access the Flower monitoring interface at `http://localhost:5555` to:
- Monitor worker status and performance
- View task progress and results
- Manage queues and workers
- Access task logs and metrics

### API Endpoints

The system provides comprehensive monitoring APIs:

```bash
# System status
curl http://localhost:8080/api/celery/status

# Active tasks
curl http://localhost:8080/api/celery/tasks

# Scheduled tasks
curl http://localhost:8080/api/celery/scheduled-tasks

# Textile ERP specific status
curl http://localhost:8080/api/textile-erp/status

# Schedule a new task
curl -X POST http://localhost:8080/api/celery/schedule-task \
  -H "Content-Type: application/json" \
  -d '{
    "token": "admin_token",
    "task_name": "agent_mcp.tasks.textile_tasks.process_sensor_batch",
    "args": ["batch_123", []],
    "queue": "sensor_data"
  }'

# Cancel a task
curl -X POST http://localhost:8080/api/celery/cancel-task \
  -H "Content-Type: application/json" \
  -d '{
    "token": "admin_token",
    "task_id": "task_id_here",
    "terminate": false
  }'
```

### Command Line Monitoring

```bash
# Check worker status
./start_workers.sh status

# View logs
./start_workers.sh logs
./start_workers.sh logs high_priority

# Worker management
./start_workers.sh stop
./start_workers.sh restart
```

### Celery Command Line Tools

```bash
# Inspect active tasks
celery -A agent_mcp.core.celery_config.celery_app inspect active

# Monitor tasks in real-time
celery -A agent_mcp.core.celery_config.celery_app events

# Worker statistics
celery -A agent_mcp.core.celery_config.celery_app inspect stats

# Purge all queues
celery -A agent_mcp.core.celery_config.celery_app purge
```

## Production Deployment

### Using Supervisor

Create `/etc/supervisor/conf.d/textile-erp-celery.conf`:

```ini
[group:textile-erp]
programs=celery-high-priority,celery-production,celery-maintenance,celery-reports,celery-beat,flower

[program:celery-high-priority]
command=/path/to/venv/bin/python /path/to/project/start_celery_worker.py --high-priority
directory=/path/to/project
user=celery
numprocs=1
stdout_logfile=/var/log/celery/high-priority.log
stderr_logfile=/var/log/celery/high-priority.log
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=600
killasgroup=true
priority=998

[program:celery-production]
command=/path/to/venv/bin/python /path/to/project/start_celery_worker.py --production
directory=/path/to/project
user=celery
numprocs=1
stdout_logfile=/var/log/celery/production.log
stderr_logfile=/var/log/celery/production.log
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=600
killasgroup=true
priority=997

[program:celery-maintenance]
command=/path/to/venv/bin/python /path/to/project/start_celery_worker.py --maintenance
directory=/path/to/project
user=celery
numprocs=1
stdout_logfile=/var/log/celery/maintenance.log
stderr_logfile=/var/log/celery/maintenance.log
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=600
killasgroup=true
priority=996

[program:celery-reports]
command=/path/to/venv/bin/python /path/to/project/start_celery_worker.py --reports
directory=/path/to/project
user=celery
numprocs=1
stdout_logfile=/var/log/celery/reports.log
stderr_logfile=/var/log/celery/reports.log
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=600
killasgroup=true
priority=995

[program:celery-beat]
command=/path/to/venv/bin/python /path/to/project/start_celery_worker.py beat
directory=/path/to/project
user=celery
numprocs=1
stdout_logfile=/var/log/celery/beat.log
stderr_logfile=/var/log/celery/beat.log
autostart=true
autorestart=true
startsecs=10
priority=999

[program:flower]
command=/path/to/venv/bin/python /path/to/project/start_celery_worker.py flower --flower-port 5555
directory=/path/to/project
user=celery
numprocs=1
stdout_logfile=/var/log/celery/flower.log
stderr_logfile=/var/log/celery/flower.log
autostart=true
autorestart=true
startsecs=10
priority=994
```

### Using systemd

Create individual service files in `/etc/systemd/system/`:

```ini
# /etc/systemd/system/textile-erp-celery@.service
[Unit]
Description=Textile ERP Celery Worker (%i)
After=network.target redis.service
Wants=redis.service

[Service]
Type=exec
User=celery
Group=celery
WorkingDirectory=/path/to/project
ExecStart=/path/to/venv/bin/python start_celery_worker.py %i
Restart=always
RestartSec=30
KillSignal=SIGTERM
TimeoutStopSec=300
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start services:
```bash
sudo systemctl enable textile-erp-celery@--high-priority
sudo systemctl enable textile-erp-celery@--production
sudo systemctl enable textile-erp-celery@--maintenance
sudo systemctl enable textile-erp-celery@--reports
sudo systemctl enable textile-erp-celery@beat

sudo systemctl start textile-erp-celery@--high-priority
sudo systemctl start textile-erp-celery@--production
sudo systemctl start textile-erp-celery@--maintenance
sudo systemctl start textile-erp-celery@--reports
sudo systemctl start textile-erp-celery@beat
```

## Task Examples

### Scheduling Tasks via Python API

```python
from agent_mcp.tasks.scheduler import (
    schedule_daily_task,
    schedule_interval_task,
    schedule_maintenance_task
)

# Schedule daily sensor data aggregation
task_id = schedule_daily_task(
    "agent_mcp.tasks.textile_tasks.aggregate_sensor_data",
    hour=6,
    minute=0,
    args=["daily"]
)

# Schedule periodic sensor batch processing
interval_task = schedule_interval_task(
    "agent_mcp.tasks.textile_tasks.process_sensor_batch",
    seconds=300,  # Every 5 minutes
    args=["auto_batch"]
)

# Schedule maintenance during maintenance window
maintenance_task = schedule_maintenance_task(
    "agent_mcp.tasks.textile_tasks.schedule_maintenance",
    args=["MACHINE_001", "PREVENTIVE"]
)
```

### Direct Task Execution

```python
from agent_mcp.core.celery_config import celery_app

# Execute task immediately
result = celery_app.send_task(
    'agent_mcp.tasks.textile_tasks.optimize_production_schedule',
    queue='production'
)

# Execute with delay
result = celery_app.send_task(
    'agent_mcp.tasks.textile_tasks.generate_daily_report',
    countdown=3600,  # 1 hour delay
    queue='reports'
)

# Get result
print(result.get(timeout=300))
```

## Troubleshooting

### Common Issues

1. **Redis Connection Error**:
```bash
# Check Redis status
sudo systemctl status redis
redis-cli ping

# Check Redis logs
sudo journalctl -u redis -f
```

2. **Worker Not Starting**:
```bash
# Check worker logs
./start_workers.sh logs worker_name

# Test Celery configuration
celery -A agent_mcp.core.celery_config.celery_app inspect ping
```

3. **Tasks Not Processing**:
```bash
# Check queue status
celery -A agent_mcp.core.celery_config.celery_app inspect active_queues

# Purge stuck queues
celery -A agent_mcp.core.celery_config.celery_app purge

# Check worker registration
celery -A agent_mcp.core.celery_config.celery_app inspect registered
```

4. **Memory Issues**:
```bash
# Monitor worker memory usage
celery -A agent_mcp.core.celery_config.celery_app inspect stats

# Restart workers with memory limits
python start_celery_worker.py worker --max-memory-per-child 204800
```

### Debugging

Enable debug logging:
```bash
export CELERY_LOG_LEVEL=DEBUG
python start_celery_worker.py worker --log-level DEBUG
```

Monitor tasks:
```bash
celery -A agent_mcp.core.celery_config.celery_app events --dump
```

## Performance Tuning

### Worker Configuration
- Set appropriate concurrency based on CPU cores
- Use prefork pool for CPU-bound tasks
- Set task time limits to prevent hanging tasks
- Configure memory limits to prevent memory leaks

### Redis Optimization
```redis
# In redis.conf
maxmemory-policy allkeys-lru
tcp-keepalive 300
timeout 300
```

### Queue Management
- Separate queues by priority and resource requirements
- Use appropriate routing to balance load
- Monitor queue lengths and worker utilization

## Security Considerations

1. **Redis Security**:
   - Use authentication (`requirepass`)
   - Bind to localhost only in production
   - Use SSL/TLS for remote connections

2. **Network Security**:
   - Firewall rules for Redis port (6379)
   - VPN or private networks for multi-server setups

3. **Application Security**:
   - Validate task arguments
   - Implement proper error handling
   - Use secure serialization

## Maintenance

### Regular Tasks
- Monitor disk space for logs
- Rotate log files
- Monitor Redis memory usage
- Review failed tasks
- Update dependencies

### Health Checks
```bash
# Check system health
curl http://localhost:8080/api/celery/status
curl http://localhost:8080/api/textile-erp/status

# Worker health check script
#!/bin/bash
workers=$(celery -A agent_mcp.core.celery_config.celery_app inspect ping | grep -c "pong")
if [ "$workers" -lt 4 ]; then
    echo "WARNING: Only $workers workers responding"
    # Restart workers or send alert
fi
```

This completes the Celery integration setup for the textile ERP system. The system is now ready for production deployment with comprehensive monitoring, error handling, and task management capabilities.