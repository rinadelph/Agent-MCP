# agent_mcp/tasks/scheduler.py
"""
Task scheduler and management for the Textile ERP Celery system.
Handles dynamic task scheduling, priority management, and periodic task coordination.
"""

import json
import logging
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum

from celery import schedules
from celery.beat import ScheduleEntry
from celery.schedules import crontab, schedule

from ..core.celery_config import celery_app
from ..core.config import logger
from ..db.connection import get_db_connection
from ..db.actions.textile_erp_actions import TextileERPActions

# Configure scheduler logger
scheduler_logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    REVOKED = "revoked"


@dataclass
class ScheduledTask:
    """Represents a scheduled task configuration."""
    task_id: str
    task_name: str
    schedule_type: str  # 'cron', 'interval', 'once'
    schedule_config: Dict[str, Any]
    args: List[Any]
    kwargs: Dict[str, Any]
    priority: TaskPriority
    enabled: bool
    created_at: datetime
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    run_count: int = 0
    failure_count: int = 0
    max_retries: int = 3
    timeout: Optional[int] = None
    expires: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class TextileERPScheduler:
    """
    Dynamic task scheduler for the Textile ERP system.
    Manages periodic tasks, maintenance windows, and priority-based scheduling.
    """
    
    def __init__(self):
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.maintenance_windows: List[Dict[str, Any]] = []
        self._load_scheduled_tasks()
        self._load_maintenance_windows()
    
    def _load_scheduled_tasks(self):
        """Load scheduled tasks from database."""
        try:
            with get_db_connection() as conn:
                erp_actions = TextileERPActions(conn)
                tasks = erp_actions.get_scheduled_tasks()
                
                for task_data in tasks:
                    task = ScheduledTask(
                        task_id=task_data["task_id"],
                        task_name=task_data["task_name"],
                        schedule_type=task_data["schedule_type"],
                        schedule_config=json.loads(task_data["schedule_config"]),
                        args=json.loads(task_data.get("args", "[]")),
                        kwargs=json.loads(task_data.get("kwargs", "{}")),
                        priority=TaskPriority(task_data["priority"]),
                        enabled=task_data["enabled"],
                        created_at=datetime.fromisoformat(task_data["created_at"]),
                        last_run_at=datetime.fromisoformat(task_data["last_run_at"]) if task_data.get("last_run_at") else None,
                        next_run_at=datetime.fromisoformat(task_data["next_run_at"]) if task_data.get("next_run_at") else None,
                        run_count=task_data.get("run_count", 0),
                        failure_count=task_data.get("failure_count", 0),
                        max_retries=task_data.get("max_retries", 3),
                        timeout=task_data.get("timeout"),
                        expires=datetime.fromisoformat(task_data["expires"]) if task_data.get("expires") else None,
                        metadata=json.loads(task_data.get("metadata", "{}"))
                    )
                    self.scheduled_tasks[task.task_id] = task
                    
            scheduler_logger.info(f"Loaded {len(self.scheduled_tasks)} scheduled tasks from database")
            
        except Exception as e:
            scheduler_logger.error(f"Error loading scheduled tasks: {e}")
    
    def _load_maintenance_windows(self):
        """Load maintenance windows configuration."""
        try:
            with get_db_connection() as conn:
                erp_actions = TextileERPActions(conn)
                self.maintenance_windows = erp_actions.get_maintenance_windows()
                
            scheduler_logger.info(f"Loaded {len(self.maintenance_windows)} maintenance windows")
            
        except Exception as e:
            scheduler_logger.error(f"Error loading maintenance windows: {e}")
    
    def add_scheduled_task(
        self,
        task_name: str,
        schedule_config: Dict[str, Any],
        schedule_type: str = "cron",
        args: List[Any] = None,
        kwargs: Dict[str, Any] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        enabled: bool = True,
        max_retries: int = 3,
        timeout: Optional[int] = None,
        expires: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a new scheduled task.
        
        Args:
            task_name: Name of the Celery task to execute
            schedule_config: Schedule configuration (cron fields, interval, etc.)
            schedule_type: Type of schedule ('cron', 'interval', 'once')
            args: Task arguments
            kwargs: Task keyword arguments
            priority: Task priority level
            enabled: Whether the task is enabled
            max_retries: Maximum retry attempts
            timeout: Task timeout in seconds
            expires: Task expiration time
            metadata: Additional metadata
            
        Returns:
            str: Task ID
        """
        try:
            task_id = f"scheduled_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{len(self.scheduled_tasks)}"
            
            # Calculate next run time
            next_run_at = self._calculate_next_run(schedule_type, schedule_config)
            
            scheduled_task = ScheduledTask(
                task_id=task_id,
                task_name=task_name,
                schedule_type=schedule_type,
                schedule_config=schedule_config,
                args=args or [],
                kwargs=kwargs or {},
                priority=priority,
                enabled=enabled,
                created_at=datetime.utcnow(),
                next_run_at=next_run_at,
                max_retries=max_retries,
                timeout=timeout,
                expires=expires,
                metadata=metadata or {}
            )
            
            # Store in database
            with get_db_connection() as conn:
                erp_actions = TextileERPActions(conn)
                erp_actions.create_scheduled_task(asdict(scheduled_task))
                conn.commit()
            
            # Add to local cache
            self.scheduled_tasks[task_id] = scheduled_task
            
            # Register with Celery Beat if it's a recurring task
            if schedule_type in ['cron', 'interval'] and enabled:
                self._register_celery_beat_task(scheduled_task)
            
            scheduler_logger.info(f"Added scheduled task: {task_id} -> {task_name}")
            return task_id
            
        except Exception as e:
            scheduler_logger.error(f"Error adding scheduled task: {e}")
            raise
    
    def remove_scheduled_task(self, task_id: str) -> bool:
        """
        Remove a scheduled task.
        
        Args:
            task_id: ID of the task to remove
            
        Returns:
            bool: Success status
        """
        try:
            if task_id not in self.scheduled_tasks:
                return False
            
            # Remove from database
            with get_db_connection() as conn:
                erp_actions = TextileERPActions(conn)
                erp_actions.delete_scheduled_task(task_id)
                conn.commit()
            
            # Remove from local cache
            task = self.scheduled_tasks.pop(task_id)
            
            # Unregister from Celery Beat
            self._unregister_celery_beat_task(task.task_id)
            
            scheduler_logger.info(f"Removed scheduled task: {task_id}")
            return True
            
        except Exception as e:
            scheduler_logger.error(f"Error removing scheduled task {task_id}: {e}")
            return False
    
    def update_scheduled_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a scheduled task.
        
        Args:
            task_id: ID of the task to update
            updates: Dictionary of fields to update
            
        Returns:
            bool: Success status
        """
        try:
            if task_id not in self.scheduled_tasks:
                return False
            
            task = self.scheduled_tasks[task_id]
            
            # Update fields
            for field, value in updates.items():
                if hasattr(task, field):
                    if field == 'priority' and isinstance(value, str):
                        value = TaskPriority(value)
                    elif field in ['created_at', 'last_run_at', 'next_run_at', 'expires'] and isinstance(value, str):
                        value = datetime.fromisoformat(value)
                    setattr(task, field, value)
            
            # Recalculate next run time if schedule changed
            if 'schedule_config' in updates or 'schedule_type' in updates:
                task.next_run_at = self._calculate_next_run(task.schedule_type, task.schedule_config)
            
            # Update in database
            with get_db_connection() as conn:
                erp_actions = TextileERPActions(conn)
                erp_actions.update_scheduled_task(task_id, asdict(task))
                conn.commit()
            
            # Re-register with Celery Beat if needed
            if 'enabled' in updates or 'schedule_config' in updates:
                self._unregister_celery_beat_task(task_id)
                if task.enabled and task.schedule_type in ['cron', 'interval']:
                    self._register_celery_beat_task(task)
            
            scheduler_logger.info(f"Updated scheduled task: {task_id}")
            return True
            
        except Exception as e:
            scheduler_logger.error(f"Error updating scheduled task {task_id}: {e}")
            return False
    
    def get_scheduled_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a scheduled task by ID."""
        return self.scheduled_tasks.get(task_id)
    
    def list_scheduled_tasks(self, enabled_only: bool = False) -> List[ScheduledTask]:
        """List all scheduled tasks."""
        tasks = list(self.scheduled_tasks.values())
        if enabled_only:
            tasks = [task for task in tasks if task.enabled]
        return sorted(tasks, key=lambda x: x.next_run_at or datetime.min)
    
    def execute_task_now(self, task_id: str, force: bool = False) -> Optional[str]:
        """
        Execute a scheduled task immediately.
        
        Args:
            task_id: ID of the task to execute
            force: Force execution even if task is disabled
            
        Returns:
            str: Celery task ID if successful, None otherwise
        """
        try:
            task = self.scheduled_tasks.get(task_id)
            if not task:
                return None
            
            if not task.enabled and not force:
                scheduler_logger.warning(f"Task {task_id} is disabled, use force=True to execute")
                return None
            
            # Check if task has expired
            if task.expires and datetime.utcnow() > task.expires:
                scheduler_logger.warning(f"Task {task_id} has expired")
                return None
            
            # Determine queue based on priority
            queue = self._get_queue_for_priority(task.priority)
            
            # Execute the task
            celery_task = celery_app.send_task(
                task.task_name,
                args=task.args,
                kwargs=task.kwargs,
                queue=queue,
                countdown=0,
                expires=task.expires,
                retry=True,
                retry_policy={
                    'max_retries': task.max_retries,
                    'interval_start': 60,
                    'interval_step': 60,
                    'interval_max': 600
                },
                soft_time_limit=task.timeout
            )
            
            # Update task execution info
            task.last_run_at = datetime.utcnow()
            task.run_count += 1
            
            # Calculate next run time if it's a recurring task
            if task.schedule_type in ['cron', 'interval']:
                task.next_run_at = self._calculate_next_run(task.schedule_type, task.schedule_config)
            
            # Update in database
            with get_db_connection() as conn:
                erp_actions = TextileERPActions(conn)
                erp_actions.update_scheduled_task(task_id, asdict(task))
                conn.commit()
            
            scheduler_logger.info(f"Executed task {task_id}: {celery_task.id}")
            return celery_task.id
            
        except Exception as e:
            scheduler_logger.error(f"Error executing task {task_id}: {e}")
            return None
    
    def is_maintenance_window(self, check_time: Optional[datetime] = None) -> bool:
        """
        Check if current time is within a maintenance window.
        
        Args:
            check_time: Time to check, defaults to current time
            
        Returns:
            bool: True if within maintenance window
        """
        if not check_time:
            check_time = datetime.utcnow()
        
        current_time = check_time.time()
        current_day = check_time.weekday()  # 0=Monday, 6=Sunday
        
        for window in self.maintenance_windows:
            # Check if day matches
            if window.get("days") and current_day not in window["days"]:
                continue
            
            # Check if time is within window
            start_time = time.fromisoformat(window["start_time"])
            end_time = time.fromisoformat(window["end_time"])
            
            if start_time <= end_time:
                # Same day window
                if start_time <= current_time <= end_time:
                    return True
            else:
                # Overnight window
                if current_time >= start_time or current_time <= end_time:
                    return True
        
        return False
    
    def get_next_maintenance_window(self, after_time: Optional[datetime] = None) -> Optional[datetime]:
        """
        Get the start time of the next maintenance window.
        
        Args:
            after_time: Look for windows after this time, defaults to current time
            
        Returns:
            datetime: Start of next maintenance window, or None if no windows defined
        """
        if not after_time:
            after_time = datetime.utcnow()
        
        if not self.maintenance_windows:
            return None
        
        # Look ahead up to 7 days
        for days_ahead in range(8):
            check_date = (after_time + timedelta(days=days_ahead)).date()
            check_weekday = check_date.weekday()
            
            for window in self.maintenance_windows:
                if window.get("days") and check_weekday not in window["days"]:
                    continue
                
                window_start = datetime.combine(check_date, time.fromisoformat(window["start_time"]))
                
                # If it's the same day as after_time, make sure window hasn't passed
                if days_ahead == 0 and window_start <= after_time:
                    continue
                
                return window_start
        
        return None
    
    def schedule_maintenance_task(
        self,
        task_name: str,
        args: List[Any] = None,
        kwargs: Dict[str, Any] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        preferred_window: Optional[datetime] = None
    ) -> Optional[str]:
        """
        Schedule a task to run during the next maintenance window.
        
        Args:
            task_name: Name of the task to schedule
            args: Task arguments
            kwargs: Task keyword arguments  
            priority: Task priority
            preferred_window: Preferred maintenance window start time
            
        Returns:
            str: Scheduled task ID if successful
        """
        try:
            # Find next maintenance window
            target_time = preferred_window or self.get_next_maintenance_window()
            
            if not target_time:
                scheduler_logger.warning("No maintenance windows defined, scheduling for immediate execution")
                target_time = datetime.utcnow() + timedelta(minutes=5)
            
            # Create one-time scheduled task
            return self.add_scheduled_task(
                task_name=task_name,
                schedule_type="once",
                schedule_config={"run_at": target_time.isoformat()},
                args=args,
                kwargs=kwargs,
                priority=priority,
                metadata={"scheduled_for": "maintenance_window"}
            )
            
        except Exception as e:
            scheduler_logger.error(f"Error scheduling maintenance task: {e}")
            return None
    
    def get_task_statistics(self) -> Dict[str, Any]:
        """Get statistics about scheduled tasks."""
        try:
            total_tasks = len(self.scheduled_tasks)
            enabled_tasks = sum(1 for task in self.scheduled_tasks.values() if task.enabled)
            disabled_tasks = total_tasks - enabled_tasks
            
            # Group by priority
            priority_counts = {}
            for priority in TaskPriority:
                priority_counts[priority.value] = sum(
                    1 for task in self.scheduled_tasks.values() if task.priority == priority
                )
            
            # Group by schedule type
            schedule_type_counts = {}
            for task in self.scheduled_tasks.values():
                schedule_type_counts[task.schedule_type] = schedule_type_counts.get(task.schedule_type, 0) + 1
            
            # Find next task to run
            next_task = None
            next_run_time = None
            for task in self.scheduled_tasks.values():
                if task.enabled and task.next_run_at:
                    if not next_run_time or task.next_run_at < next_run_time:
                        next_task = task.task_id
                        next_run_time = task.next_run_at
            
            return {
                "total_tasks": total_tasks,
                "enabled_tasks": enabled_tasks,
                "disabled_tasks": disabled_tasks,
                "priority_distribution": priority_counts,
                "schedule_type_distribution": schedule_type_counts,
                "next_task_id": next_task,
                "next_run_time": next_run_time.isoformat() if next_run_time else None,
                "maintenance_windows_configured": len(self.maintenance_windows),
                "in_maintenance_window": self.is_maintenance_window(),
                "next_maintenance_window": self.get_next_maintenance_window().isoformat() if self.get_next_maintenance_window() else None
            }
            
        except Exception as e:
            scheduler_logger.error(f"Error getting task statistics: {e}")
            return {}
    
    def _calculate_next_run(self, schedule_type: str, schedule_config: Dict[str, Any]) -> Optional[datetime]:
        """Calculate the next run time for a task."""
        try:
            if schedule_type == "once":
                run_at = schedule_config.get("run_at")
                return datetime.fromisoformat(run_at) if run_at else None
            
            elif schedule_type == "interval":
                interval_seconds = schedule_config.get("seconds", 0)
                return datetime.utcnow() + timedelta(seconds=interval_seconds)
            
            elif schedule_type == "cron":
                # Create crontab schedule
                cron_schedule = crontab(
                    minute=schedule_config.get("minute", "*"),
                    hour=schedule_config.get("hour", "*"),
                    day_of_week=schedule_config.get("day_of_week", "*"),
                    day_of_month=schedule_config.get("day_of_month", "*"),
                    month_of_year=schedule_config.get("month_of_year", "*")
                )
                
                # Calculate next run time
                now = datetime.utcnow()
                return cron_schedule.next(now)
            
            return None
            
        except Exception as e:
            scheduler_logger.error(f"Error calculating next run time: {e}")
            return None
    
    def _get_queue_for_priority(self, priority: TaskPriority) -> str:
        """Get the appropriate queue for a task priority."""
        queue_mapping = {
            TaskPriority.LOW: "low_priority",
            TaskPriority.NORMAL: "default",
            TaskPriority.HIGH: "high_priority",
            TaskPriority.CRITICAL: "high_priority"
        }
        return queue_mapping.get(priority, "default")
    
    def _register_celery_beat_task(self, task: ScheduledTask):
        """Register a task with Celery Beat."""
        try:
            if task.schedule_type == "cron":
                schedule_obj = crontab(
                    minute=task.schedule_config.get("minute", "*"),
                    hour=task.schedule_config.get("hour", "*"),
                    day_of_week=task.schedule_config.get("day_of_week", "*"),
                    day_of_month=task.schedule_config.get("day_of_month", "*"),
                    month_of_year=task.schedule_config.get("month_of_year", "*")
                )
            elif task.schedule_type == "interval":
                interval_seconds = task.schedule_config.get("seconds", 3600)
                schedule_obj = schedule(run_every=timedelta(seconds=interval_seconds))
            else:
                return  # Don't register one-time tasks
            
            # Add to Celery Beat schedule
            celery_app.conf.beat_schedule[task.task_id] = {
                'task': task.task_name,
                'schedule': schedule_obj,
                'args': task.args,
                'kwargs': task.kwargs,
                'options': {
                    'queue': self._get_queue_for_priority(task.priority),
                    'expires': task.expires,
                    'retry': True,
                    'retry_policy': {
                        'max_retries': task.max_retries,
                        'interval_start': 60,
                        'interval_step': 60,
                        'interval_max': 600
                    }
                }
            }
            
            scheduler_logger.debug(f"Registered Celery Beat task: {task.task_id}")
            
        except Exception as e:
            scheduler_logger.error(f"Error registering Celery Beat task {task.task_id}: {e}")
    
    def _unregister_celery_beat_task(self, task_id: str):
        """Unregister a task from Celery Beat."""
        try:
            if task_id in celery_app.conf.beat_schedule:
                del celery_app.conf.beat_schedule[task_id]
                scheduler_logger.debug(f"Unregistered Celery Beat task: {task_id}")
        except Exception as e:
            scheduler_logger.error(f"Error unregistering Celery Beat task {task_id}: {e}")


# Global scheduler instance
textile_scheduler = TextileERPScheduler()


# Convenience functions for common scheduling patterns
def schedule_daily_task(task_name: str, hour: int, minute: int = 0, args: List[Any] = None, kwargs: Dict[str, Any] = None) -> str:
    """Schedule a task to run daily at specified time."""
    return textile_scheduler.add_scheduled_task(
        task_name=task_name,
        schedule_type="cron",
        schedule_config={"hour": hour, "minute": minute},
        args=args,
        kwargs=kwargs
    )


def schedule_weekly_task(task_name: str, day_of_week: int, hour: int, minute: int = 0, args: List[Any] = None, kwargs: Dict[str, Any] = None) -> str:
    """Schedule a task to run weekly on specified day and time."""
    return textile_scheduler.add_scheduled_task(
        task_name=task_name,
        schedule_type="cron",
        schedule_config={"day_of_week": day_of_week, "hour": hour, "minute": minute},
        args=args,
        kwargs=kwargs
    )


def schedule_monthly_task(task_name: str, day: int, hour: int, minute: int = 0, args: List[Any] = None, kwargs: Dict[str, Any] = None) -> str:
    """Schedule a task to run monthly on specified day and time."""
    return textile_scheduler.add_scheduled_task(
        task_name=task_name,
        schedule_type="cron",
        schedule_config={"day_of_month": day, "hour": hour, "minute": minute},
        args=args,
        kwargs=kwargs
    )


def schedule_interval_task(task_name: str, seconds: int, args: List[Any] = None, kwargs: Dict[str, Any] = None) -> str:
    """Schedule a task to run at regular intervals."""
    return textile_scheduler.add_scheduled_task(
        task_name=task_name,
        schedule_type="interval",
        schedule_config={"seconds": seconds},
        args=args,
        kwargs=kwargs
    )


def schedule_one_time_task(task_name: str, run_at: datetime, args: List[Any] = None, kwargs: Dict[str, Any] = None) -> str:
    """Schedule a task to run once at specified time."""
    return textile_scheduler.add_scheduled_task(
        task_name=task_name,
        schedule_type="once",
        schedule_config={"run_at": run_at.isoformat()},
        args=args,
        kwargs=kwargs
    )


def schedule_high_priority_task(task_name: str, run_at: datetime, args: List[Any] = None, kwargs: Dict[str, Any] = None) -> str:
    """Schedule a high-priority task to run once."""
    return textile_scheduler.add_scheduled_task(
        task_name=task_name,
        schedule_type="once",
        schedule_config={"run_at": run_at.isoformat()},
        args=args,
        kwargs=kwargs,
        priority=TaskPriority.HIGH
    )


def schedule_maintenance_task(task_name: str, args: List[Any] = None, kwargs: Dict[str, Any] = None) -> Optional[str]:
    """Schedule a task to run during the next maintenance window."""
    return textile_scheduler.schedule_maintenance_task(task_name, args, kwargs)


# Celery task for dynamic task execution
@celery_app.task(bind=True, base=object)
def execute_scheduled_task(self, task_id: str):
    """Execute a dynamically scheduled task."""
    try:
        result = textile_scheduler.execute_task_now(task_id)
        if result:
            scheduler_logger.info(f"Dynamic task {task_id} executed successfully: {result}")
            return {"status": "success", "celery_task_id": result}
        else:
            scheduler_logger.error(f"Failed to execute dynamic task {task_id}")
            return {"status": "error", "message": "Task execution failed"}
            
    except Exception as exc:
        scheduler_logger.error(f"Error executing scheduled task {task_id}: {exc}")
        raise self.retry(exc=exc, countdown=60, max_retries=3)


# Task management API functions
def get_scheduler_status() -> Dict[str, Any]:
    """Get current scheduler status and statistics."""
    return textile_scheduler.get_task_statistics()


def list_all_scheduled_tasks() -> List[Dict[str, Any]]:
    """List all scheduled tasks."""
    tasks = textile_scheduler.list_scheduled_tasks()
    return [asdict(task) for task in tasks]


def get_scheduled_task_info(task_id: str) -> Optional[Dict[str, Any]]:
    """Get information about a specific scheduled task."""
    task = textile_scheduler.get_scheduled_task(task_id)
    return asdict(task) if task else None


def enable_scheduled_task(task_id: str) -> bool:
    """Enable a scheduled task."""
    return textile_scheduler.update_scheduled_task(task_id, {"enabled": True})


def disable_scheduled_task(task_id: str) -> bool:
    """Disable a scheduled task."""
    return textile_scheduler.update_scheduled_task(task_id, {"enabled": False})


def delete_scheduled_task(task_id: str) -> bool:
    """Delete a scheduled task."""
    return textile_scheduler.remove_scheduled_task(task_id)


def is_maintenance_time() -> bool:
    """Check if current time is within a maintenance window."""
    return textile_scheduler.is_maintenance_window()


def get_next_maintenance_time() -> Optional[str]:
    """Get the next maintenance window start time."""
    next_window = textile_scheduler.get_next_maintenance_window()
    return next_window.isoformat() if next_window else None