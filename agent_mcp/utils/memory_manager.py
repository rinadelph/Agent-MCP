# Memory Management System
"""
Memory management system for Agent-MCP to optimize memory usage,
implement garbage collection, and provide monitoring capabilities.
"""

import gc
import psutil
import time
import threading
import weakref
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
import logging
from collections import defaultdict, deque
import json
from pathlib import Path

from ..core.config import logger


class MemoryAlertLevel(Enum):
    """Memory alert levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MemoryUsage:
    """Memory usage information."""
    total_memory: int
    available_memory: int
    used_memory: int
    memory_percentage: float
    timestamp: float = field(default_factory=time.time)
    
    @property
    def free_memory(self) -> int:
        return self.available_memory
    
    @property
    def used_percentage(self) -> float:
        return self.memory_percentage


@dataclass
class MemoryAlert:
    """Memory alert information."""
    level: MemoryAlertLevel
    message: str
    current_usage: MemoryUsage
    threshold: float
    timestamp: float = field(default_factory=time.time)


class MemoryManager:
    """Manages memory usage and garbage collection."""
    
    def __init__(self, 
                 low_threshold: float = 0.6,
                 medium_threshold: float = 0.75,
                 high_threshold: float = 0.85,
                 critical_threshold: float = 0.95,
                 gc_threshold: float = 0.8,
                 monitoring_interval: float = 30.0):
        
        self.low_threshold = low_threshold
        self.medium_threshold = medium_threshold
        self.high_threshold = high_threshold
        self.critical_threshold = critical_threshold
        self.gc_threshold = gc_threshold
        self.monitoring_interval = monitoring_interval
        
        self.memory_history: deque = deque(maxlen=1000)
        self.alerts: List[MemoryAlert] = []
        self.alert_callbacks: List[Callable[[MemoryAlert], None]] = []
        
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        # Memory tracking
        self.object_tracker: Dict[int, Dict[str, Any]] = {}
        self.weak_refs: Set[weakref.ref] = set()
        
        # Performance metrics
        self.gc_stats = {
            "total_collections": 0,
            "last_collection_time": 0,
            "average_collection_time": 0.0,
            "memory_freed_total": 0
        }
        
        # Initialize monitoring
        self._start_monitoring()
    
    def get_memory_usage(self) -> MemoryUsage:
        """Get current memory usage."""
        memory = psutil.virtual_memory()
        return MemoryUsage(
            total_memory=memory.total,
            available_memory=memory.available,
            used_memory=memory.used,
            memory_percentage=memory.percent / 100.0
        )
    
    def get_memory_alert_level(self, usage: MemoryUsage) -> MemoryAlertLevel:
        """Determine memory alert level based on usage."""
        if usage.memory_percentage >= self.critical_threshold:
            return MemoryAlertLevel.CRITICAL
        elif usage.memory_percentage >= self.high_threshold:
            return MemoryAlertLevel.HIGH
        elif usage.memory_percentage >= self.medium_threshold:
            return MemoryAlertLevel.MEDIUM
        elif usage.memory_percentage >= self.low_threshold:
            return MemoryAlertLevel.LOW
        else:
            return MemoryAlertLevel.LOW
    
    def check_memory_alerts(self, usage: MemoryUsage) -> Optional[MemoryAlert]:
        """Check if memory usage triggers alerts."""
        alert_level = self.get_memory_alert_level(usage)
        
        if alert_level != MemoryAlertLevel.LOW:
            alert = MemoryAlert(
                level=alert_level,
                message=f"Memory usage is {usage.memory_percentage:.1%}",
                current_usage=usage,
                threshold=self._get_threshold_for_level(alert_level)
            )
            
            self.alerts.append(alert)
            self._notify_alert_callbacks(alert)
            
            return alert
        
        return None
    
    def _get_threshold_for_level(self, level: MemoryAlertLevel) -> float:
        """Get threshold value for alert level."""
        thresholds = {
            MemoryAlertLevel.LOW: self.low_threshold,
            MemoryAlertLevel.MEDIUM: self.medium_threshold,
            MemoryAlertLevel.HIGH: self.high_threshold,
            MemoryAlertLevel.CRITICAL: self.critical_threshold
        }
        return thresholds.get(level, 0.0)
    
    def add_alert_callback(self, callback: Callable[[MemoryAlert], None]) -> None:
        """Add a callback for memory alerts."""
        self.alert_callbacks.append(callback)
    
    def _notify_alert_callbacks(self, alert: MemoryAlert) -> None:
        """Notify all alert callbacks."""
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error in memory alert callback: {e}")
    
    def _start_monitoring(self) -> None:
        """Start memory monitoring in background thread."""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitor_memory, daemon=True)
        self.monitor_thread.start()
        logger.info("Memory monitoring started")
    
    def _monitor_memory(self) -> None:
        """Monitor memory usage in background thread."""
        while self.monitoring_active:
            try:
                usage = self.get_memory_usage()
                self.memory_history.append(usage)
                
                # Check for alerts
                alert = self.check_memory_alerts(usage)
                if alert:
                    logger.warning(f"Memory alert: {alert.message}")
                
                # Trigger garbage collection if needed
                if usage.memory_percentage >= self.gc_threshold:
                    self.trigger_garbage_collection()
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in memory monitoring: {e}")
                time.sleep(self.monitoring_interval)
    
    def trigger_garbage_collection(self, generation: int = 2) -> Dict[str, Any]:
        """Trigger garbage collection and return statistics."""
        start_time = time.time()
        start_memory = self.get_memory_usage()
        
        # Run garbage collection
        collected = gc.collect(generation)
        
        end_time = time.time()
        end_memory = self.get_memory_usage()
        
        # Calculate statistics
        collection_time = end_time - start_time
        memory_freed = start_memory.used_memory - end_memory.used_memory
        
        # Update GC stats
        self.gc_stats["total_collections"] += 1
        self.gc_stats["last_collection_time"] = end_time
        
        # Update average collection time
        total_collections = self.gc_stats["total_collections"]
        current_avg = self.gc_stats["average_collection_time"]
        new_avg = ((current_avg * (total_collections - 1)) + collection_time) / total_collections
        self.gc_stats["average_collection_time"] = new_avg
        
        self.gc_stats["memory_freed_total"] += memory_freed
        
        stats = {
            "collected_objects": collected,
            "collection_time": collection_time,
            "memory_freed": memory_freed,
            "start_memory": start_memory.used_memory,
            "end_memory": end_memory.used_memory
        }
        
        logger.info(f"Garbage collection completed: {collected} objects collected, "
                   f"{memory_freed} bytes freed in {collection_time:.3f}s")
        
        return stats
    
    def track_object(self, obj: Any, category: str = "general", 
                    metadata: Optional[Dict[str, Any]] = None) -> None:
        """Track an object for memory management."""
        obj_id = id(obj)
        self.object_tracker[obj_id] = {
            "category": category,
            "metadata": metadata or {},
            "created_at": time.time(),
            "size_estimate": self._estimate_object_size(obj)
        }
        
        # Create weak reference to detect when object is garbage collected
        weak_ref = weakref.ref(obj, lambda ref, obj_id=obj_id: self._object_collected(obj_id))
        self.weak_refs.add(weak_ref)
    
    def _object_collected(self, obj_id: int) -> None:
        """Called when a tracked object is garbage collected."""
        if obj_id in self.object_tracker:
            del self.object_tracker[obj_id]
    
    def _estimate_object_size(self, obj: Any) -> int:
        """Estimate the size of an object in bytes."""
        try:
            import sys
            return sys.getsizeof(obj)
        except:
            return 0
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics."""
        current_usage = self.get_memory_usage()
        
        # Calculate memory trends
        if len(self.memory_history) >= 2:
            recent_usage = list(self.memory_history)[-10:]  # Last 10 measurements
            avg_usage = sum(u.memory_percentage for u in recent_usage) / len(recent_usage)
            trend = "increasing" if recent_usage[-1].memory_percentage > recent_usage[0].memory_percentage else "decreasing"
        else:
            avg_usage = current_usage.memory_percentage
            trend = "stable"
        
        # Object tracking statistics
        object_stats = defaultdict(int)
        total_tracked_size = 0
        
        for obj_info in self.object_tracker.values():
            category = obj_info["category"]
            object_stats[category] += 1
            total_tracked_size += obj_info.get("size_estimate", 0)
        
        return {
            "current_usage": {
                "total_memory": current_usage.total_memory,
                "used_memory": current_usage.used_memory,
                "available_memory": current_usage.available_memory,
                "memory_percentage": current_usage.memory_percentage
            },
            "trends": {
                "average_usage": avg_usage,
                "trend": trend,
                "history_count": len(self.memory_history)
            },
            "garbage_collection": self.gc_stats.copy(),
            "object_tracking": {
                "total_tracked_objects": len(self.object_tracker),
                "total_tracked_size": total_tracked_size,
                "objects_by_category": dict(object_stats)
            },
            "alerts": {
                "total_alerts": len(self.alerts),
                "recent_alerts": len([a for a in self.alerts if time.time() - a.timestamp < 3600])
            }
        }
    
    def optimize_memory(self) -> Dict[str, Any]:
        """Perform memory optimization operations."""
        optimization_results = {
            "garbage_collection": self.trigger_garbage_collection(),
            "object_cleanup": self._cleanup_old_objects(),
            "alert_cleanup": self._cleanup_old_alerts()
        }
        
        logger.info("Memory optimization completed")
        return optimization_results
    
    def _cleanup_old_objects(self) -> Dict[str, Any]:
        """Clean up old tracked objects."""
        current_time = time.time()
        max_age = 3600  # 1 hour
        
        removed_objects = 0
        for obj_id, obj_info in list(self.object_tracker.items()):
            if current_time - obj_info["created_at"] > max_age:
                del self.object_tracker[obj_id]
                removed_objects += 1
        
        return {
            "removed_objects": removed_objects,
            "remaining_objects": len(self.object_tracker)
        }
    
    def _cleanup_old_alerts(self) -> Dict[str, Any]:
        """Clean up old alerts."""
        current_time = time.time()
        max_age = 86400  # 24 hours
        
        original_count = len(self.alerts)
        self.alerts = [alert for alert in self.alerts 
                      if current_time - alert.timestamp < max_age]
        
        removed_count = original_count - len(self.alerts)
        
        return {
            "removed_alerts": removed_count,
            "remaining_alerts": len(self.alerts)
        }
    
    def export_memory_report(self, file_path: str) -> None:
        """Export memory usage report to JSON file."""
        report = {
            "timestamp": time.time(),
            "statistics": self.get_memory_statistics(),
            "recent_alerts": [
                {
                    "level": alert.level.value,
                    "message": alert.message,
                    "timestamp": alert.timestamp,
                    "usage_percentage": alert.current_usage.memory_percentage
                }
                for alert in self.alerts[-50:]  # Last 50 alerts
            ],
            "memory_history": [
                {
                    "timestamp": usage.timestamp,
                    "memory_percentage": usage.memory_percentage,
                    "used_memory": usage.used_memory
                }
                for usage in list(self.memory_history)[-100:]  # Last 100 measurements
            ]
        }
        
        with open(file_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Memory report exported to {file_path}")
    
    def stop_monitoring(self) -> None:
        """Stop memory monitoring."""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        logger.info("Memory monitoring stopped")


# Global memory manager instance
memory_manager = MemoryManager()
