#!/usr/bin/env python3
"""
Celery Worker Startup Script for Textile ERP System.
This script starts Celery workers with appropriate configuration.
"""

import os
import sys
import signal
import logging
import argparse
from pathlib import Path
from typing import List, Optional

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agent_mcp.core.celery_config import celery_app, CELERY_APP_NAME
from agent_mcp.core.config import logger


def setup_logging():
    """Setup logging for the worker."""
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s: %(levelname)s/%(name)s] %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('celery_worker.log')
        ]
    )


def start_worker(
    queues: Optional[List[str]] = None,
    concurrency: Optional[int] = None,
    log_level: str = "INFO",
    worker_name: Optional[str] = None,
    max_tasks_per_child: Optional[int] = None,
    max_memory_per_child: Optional[int] = None
):
    """
    Start a Celery worker with specified configuration.
    
    Args:
        queues: List of queues to consume from
        concurrency: Number of concurrent worker processes
        log_level: Logging level
        worker_name: Custom worker name
        max_tasks_per_child: Max tasks per worker child process
        max_memory_per_child: Max memory per worker child process (KB)
    """
    try:
        logger.info(f"Starting Celery worker for {CELERY_APP_NAME}")
        
        # Build worker arguments
        worker_args = [
            'worker',
            '--app', CELERY_APP_NAME,
            '--loglevel', log_level,
        ]
        
        # Add queues if specified
        if queues:
            worker_args.extend(['--queues', ','.join(queues)])
        else:
            # Default queues for textile ERP
            default_queues = [
                'default',
                'high_priority',
                'sensor_data',
                'production',
                'quality_control',
                'inventory',
                'maintenance',
                'reports'
            ]
            worker_args.extend(['--queues', ','.join(default_queues)])
        
        # Add concurrency if specified
        if concurrency:
            worker_args.extend(['--concurrency', str(concurrency)])
        else:
            # Default to number of CPU cores
            import multiprocessing
            worker_args.extend(['--concurrency', str(multiprocessing.cpu_count())])
        
        # Add worker name if specified
        if worker_name:
            worker_args.extend(['--hostname', f"{worker_name}@%h"])
        else:
            # Default worker name based on queues
            queue_suffix = "_".join(queues[:2]) if queues else "textile_erp"
            worker_args.extend(['--hostname', f"worker_{queue_suffix}@%h"])
        
        # Add task limits
        if max_tasks_per_child:
            worker_args.extend(['--max-tasks-per-child', str(max_tasks_per_child)])
        else:
            worker_args.extend(['--max-tasks-per-child', '1000'])
        
        if max_memory_per_child:
            worker_args.extend(['--max-memory-per-child', str(max_memory_per_child)])
        
        # Add other useful options
        worker_args.extend([
            '--time-limit', '3600',  # 1 hour task time limit
            '--soft-time-limit', '3000',  # 50 minutes soft limit
            '--prefetch-multiplier', '1',  # Disable prefetching for better load balancing
            '--pool', 'prefork',  # Use prefork pool
            '--optimization', 'fair',  # Fair task distribution
        ])
        
        logger.info(f"Worker arguments: {' '.join(worker_args)}")
        
        # Start the worker
        celery_app.start(worker_args)
        
    except KeyboardInterrupt:
        logger.info("Worker shutdown requested by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error starting Celery worker: {e}")
        sys.exit(1)


def start_beat_scheduler():
    """Start Celery Beat scheduler for periodic tasks."""
    try:
        logger.info("Starting Celery Beat scheduler")
        
        beat_args = [
            'beat',
            '--app', CELERY_APP_NAME,
            '--loglevel', 'INFO',
            '--schedule', 'celerybeat-schedule',
            '--pidfile', 'celerybeat.pid',
        ]
        
        logger.info(f"Beat arguments: {' '.join(beat_args)}")
        celery_app.start(beat_args)
        
    except KeyboardInterrupt:
        logger.info("Beat scheduler shutdown requested by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error starting Celery Beat: {e}")
        sys.exit(1)


def start_flower_monitor(port: int = 5555):
    """Start Flower monitoring web interface."""
    try:
        logger.info(f"Starting Flower monitor on port {port}")
        
        flower_args = [
            'flower',
            '--app', CELERY_APP_NAME,
            '--port', str(port),
            '--broker_api', os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
        ]
        
        logger.info(f"Flower arguments: {' '.join(flower_args)}")
        celery_app.start(flower_args)
        
    except KeyboardInterrupt:
        logger.info("Flower monitor shutdown requested by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error starting Flower monitor: {e}")
        sys.exit(1)


def main():
    """Main entry point for the worker startup script."""
    setup_logging()
    
    parser = argparse.ArgumentParser(description='Start Celery workers for Textile ERP')
    parser.add_argument('component', choices=['worker', 'beat', 'flower', 'all'], 
                        help='Component to start')
    parser.add_argument('--queues', '-q', nargs='+', 
                        help='Queues to consume from (worker only)')
    parser.add_argument('--concurrency', '-c', type=int,
                        help='Number of concurrent processes')
    parser.add_argument('--log-level', '-l', default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                        help='Log level')
    parser.add_argument('--worker-name', '-n', 
                        help='Custom worker name')
    parser.add_argument('--max-tasks-per-child', type=int,
                        help='Max tasks per worker child process')
    parser.add_argument('--max-memory-per-child', type=int,
                        help='Max memory per worker child process (KB)')
    parser.add_argument('--flower-port', type=int, default=5555,
                        help='Port for Flower monitor (flower only)')
    
    # Predefined worker configurations
    parser.add_argument('--high-priority', action='store_true',
                        help='Start high-priority worker (high_priority, sensor_data queues)')
    parser.add_argument('--production', action='store_true',
                        help='Start production worker (production, quality_control queues)')
    parser.add_argument('--maintenance', action='store_true',
                        help='Start maintenance worker (maintenance, inventory queues)')
    parser.add_argument('--reports', action='store_true',
                        help='Start reports worker (reports, low_priority queues)')
    
    args = parser.parse_args()
    
    # Handle predefined configurations
    if args.high_priority:
        args.queues = ['high_priority', 'sensor_data']
        args.worker_name = 'high_priority_worker'
        args.concurrency = args.concurrency or 4
        
    elif args.production:
        args.queues = ['production', 'quality_control']
        args.worker_name = 'production_worker'
        args.concurrency = args.concurrency or 2
        
    elif args.maintenance:
        args.queues = ['maintenance', 'inventory']
        args.worker_name = 'maintenance_worker'
        args.concurrency = args.concurrency or 2
        
    elif args.reports:
        args.queues = ['reports', 'low_priority']
        args.worker_name = 'reports_worker'
        args.concurrency = args.concurrency or 1
    
    # Start the requested component
    if args.component == 'worker':
        start_worker(
            queues=args.queues,
            concurrency=args.concurrency,
            log_level=args.log_level,
            worker_name=args.worker_name,
            max_tasks_per_child=args.max_tasks_per_child,
            max_memory_per_child=args.max_memory_per_child
        )
    elif args.component == 'beat':
        start_beat_scheduler()
    elif args.component == 'flower':
        start_flower_monitor(args.flower_port)
    elif args.component == 'all':
        # Start all components (this would require process management)
        logger.info("Starting all components requires a process manager like supervisor")
        logger.info("Start each component in separate terminals:")
        logger.info("  python start_celery_worker.py worker")
        logger.info("  python start_celery_worker.py beat")
        logger.info("  python start_celery_worker.py flower")
        sys.exit(1)


if __name__ == '__main__':
    main()