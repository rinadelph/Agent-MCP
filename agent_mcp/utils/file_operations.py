# File Operations System
"""
Optimized file operations system for Agent-MCP with batching,
caching, change detection, and rollback capabilities.
"""

import os
import shutil
import hashlib
import time
import threading
import asyncio
from typing import Dict, List, Set, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict, deque
import json
import pickle
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent

from ..core.config import logger


@dataclass
class FileOperation:
    """Represents a file operation."""
    operation_type: str  # 'read', 'write', 'delete', 'move', 'copy'
    source_path: Optional[str] = None
    target_path: Optional[str] = None
    content: Optional[bytes] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=time.time)
    operation_id: str = field(default_factory=lambda: f"op_{int(time.time() * 1000)}")


@dataclass
class FileCache:
    """File cache entry."""
    content_hash: str
    content: bytes
    metadata: Dict[str, Any]
    last_accessed: float
    access_count: int = 0


class FileChangeHandler(FileSystemEventHandler):
    """Handles file system change events."""
    
    def __init__(self, callback: Callable[[str, str], None]):
        self.callback = callback
    
    def on_modified(self, event):
        if not event.is_directory:
            self.callback("modified", event.src_path)
    
    def on_created(self, event):
        if not event.is_directory:
            self.callback("created", event.src_path)
    
    def on_deleted(self, event):
        if not event.is_directory:
            self.callback("deleted", event.src_path)


class FileOperationsManager:
    """Manages file operations with batching, caching, and change detection."""
    
    def __init__(self, 
                 cache_size: int = 1000,
                 batch_size: int = 50,
                 batch_timeout: float = 5.0,
                 enable_watching: bool = True):
        
        self.cache_size = cache_size
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.enable_watching = enable_watching
        
        # File cache
        self.file_cache: Dict[str, FileCache] = {}
        self.cache_access_order: deque = deque()
        
        # Operation batching
        self.pending_operations: List[FileOperation] = []
        self.batch_lock = threading.Lock()
        self.batch_timer: Optional[asyncio.TimerHandle] = None
        
        # Change detection
        self.file_watchers: Dict[str, Observer] = {}
        self.change_callbacks: List[Callable[[str, str], None]] = []
        self.watched_paths: Set[str] = set()
        
        # Operation history for rollback
        self.operation_history: deque = deque(maxlen=10000)
        
        # Performance metrics
        self.metrics = {
            "total_operations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "batch_operations": 0,
            "change_events": 0
        }
        
        # Start background processing
        self._start_background_processing()
    
    def _start_background_processing(self) -> None:
        """Start background processing for file operations."""
        if self.enable_watching:
            self._start_file_watching()
    
    def _start_file_watching(self) -> None:
        """Start file system watching."""
        # This would be implemented based on specific directories to watch
        pass
    
    def _get_file_hash(self, file_path: str) -> str:
        """Get hash of file content."""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()
        except Exception:
            return ""
    
    def _update_cache_access(self, file_path: str) -> None:
        """Update cache access order."""
        if file_path in self.cache_access_order:
            self.cache_access_order.remove(file_path)
        self.cache_access_order.append(file_path)
    
    def _evict_cache_if_needed(self) -> None:
        """Evict cache entries if cache is full."""
        while len(self.file_cache) > self.cache_size:
            if self.cache_access_order:
                oldest_path = self.cache_access_order.popleft()
                if oldest_path in self.file_cache:
                    del self.file_cache[oldest_path]
    
    def read_file(self, file_path: str, use_cache: bool = True) -> Tuple[bytes, Dict[str, Any]]:
        """Read file content with caching."""
        self.metrics["total_operations"] += 1
        
        # Check cache first
        if use_cache and file_path in self.file_cache:
            cache_entry = self.file_cache[file_path]
            cache_entry.access_count += 1
            cache_entry.last_accessed = time.time()
            self._update_cache_access(file_path)
            self.metrics["cache_hits"] += 1
            
            return cache_entry.content, cache_entry.metadata
        
        # Read from disk
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # Get file metadata
            stat = os.stat(file_path)
            metadata = {
                "size": stat.st_size,
                "modified_time": stat.st_mtime,
                "created_time": stat.st_ctime,
                "permissions": stat.st_mode
            }
            
            # Cache the result
            if use_cache:
                content_hash = hashlib.md5(content).hexdigest()
                cache_entry = FileCache(
                    content_hash=content_hash,
                    content=content,
                    metadata=metadata,
                    last_accessed=time.time()
                )
                
                self.file_cache[file_path] = cache_entry
                self._update_cache_access(file_path)
                self._evict_cache_if_needed()
            
            self.metrics["cache_misses"] += 1
            return content, metadata
            
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            raise
    
    def write_file(self, file_path: str, content: bytes, 
                   metadata: Optional[Dict[str, Any]] = None) -> None:
        """Write file content with batching support."""
        operation = FileOperation(
            operation_type="write",
            target_path=file_path,
            content=content,
            metadata=metadata
        )
        
        self._add_to_batch(operation)
    
    def _add_to_batch(self, operation: FileOperation) -> None:
        """Add operation to batch queue."""
        with self.batch_lock:
            self.pending_operations.append(operation)
            
            # Execute batch if full
            if len(self.pending_operations) >= self.batch_size:
                self._execute_batch()
            else:
                # Schedule batch execution after timeout
                if self.batch_timer:
                    self.batch_timer.cancel()
                
                loop = asyncio.get_event_loop()
                self.batch_timer = loop.call_later(self.batch_timeout, self._execute_batch)
    
    def _execute_batch(self) -> None:
        """Execute pending operations in batch."""
        with self.batch_lock:
            if not self.pending_operations:
                return
            
            operations = self.pending_operations.copy()
            self.pending_operations.clear()
            
            if self.batch_timer:
                self.batch_timer.cancel()
                self.batch_timer = None
        
        # Execute operations
        for operation in operations:
            try:
                self._execute_operation(operation)
                self.operation_history.append(operation)
            except Exception as e:
                logger.error(f"Error executing operation {operation.operation_id}: {e}")
        
        self.metrics["batch_operations"] += len(operations)
    
    def _execute_operation(self, operation: FileOperation) -> None:
        """Execute a single file operation."""
        if operation.operation_type == "write":
            self._write_file_sync(operation.target_path, operation.content, operation.metadata)
        elif operation.operation_type == "delete":
            self._delete_file_sync(operation.target_path)
        elif operation.operation_type == "move":
            self._move_file_sync(operation.source_path, operation.target_path)
        elif operation.operation_type == "copy":
            self._copy_file_sync(operation.source_path, operation.target_path)
    
    def _write_file_sync(self, file_path: str, content: bytes, 
                         metadata: Optional[Dict[str, Any]] = None) -> None:
        """Write file synchronously."""
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Write file
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # Update cache
        if file_path in self.file_cache:
            del self.file_cache[file_path]
        
        # Update metadata
        if metadata:
            # Apply metadata changes (permissions, etc.)
            pass
    
    def _delete_file_sync(self, file_path: str) -> None:
        """Delete file synchronously."""
        if os.path.exists(file_path):
            os.remove(file_path)
            
            # Remove from cache
            if file_path in self.file_cache:
                del self.file_cache[file_path]
    
    def _move_file_sync(self, source_path: str, target_path: str) -> None:
        """Move file synchronously."""
        if os.path.exists(source_path):
            # Create target directory
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # Move file
            shutil.move(source_path, target_path)
            
            # Update cache
            if source_path in self.file_cache:
                cache_entry = self.file_cache.pop(source_path)
                self.file_cache[target_path] = cache_entry
    
    def _copy_file_sync(self, source_path: str, target_path: str) -> None:
        """Copy file synchronously."""
        if os.path.exists(source_path):
            # Create target directory
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # Copy file
            shutil.copy2(source_path, target_path)
            
            # Update cache
            if source_path in self.file_cache:
                source_cache = self.file_cache[source_path]
                target_cache = FileCache(
                    content_hash=source_cache.content_hash,
                    content=source_cache.content,
                    metadata=source_cache.metadata,
                    last_accessed=time.time()
                )
                self.file_cache[target_path] = target_cache
    
    def delete_file(self, file_path: str) -> None:
        """Delete file with batching support."""
        operation = FileOperation(
            operation_type="delete",
            target_path=file_path
        )
        self._add_to_batch(operation)
    
    def move_file(self, source_path: str, target_path: str) -> None:
        """Move file with batching support."""
        operation = FileOperation(
            operation_type="move",
            source_path=source_path,
            target_path=target_path
        )
        self._add_to_batch(operation)
    
    def copy_file(self, source_path: str, target_path: str) -> None:
        """Copy file with batching support."""
        operation = FileOperation(
            operation_type="copy",
            source_path=source_path,
            target_path=target_path
        )
        self._add_to_batch(operation)
    
    def watch_directory(self, directory_path: str, 
                       callback: Callable[[str, str], None]) -> None:
        """Watch a directory for changes."""
        if directory_path in self.watched_paths:
            return
        
        try:
            observer = Observer()
            handler = FileChangeHandler(callback)
            observer.schedule(handler, directory_path, recursive=True)
            observer.start()
            
            self.file_watchers[directory_path] = observer
            self.watched_paths.add(directory_path)
            self.change_callbacks.append(callback)
            
            logger.info(f"Started watching directory: {directory_path}")
            
        except Exception as e:
            logger.error(f"Error watching directory {directory_path}: {e}")
    
    def unwatch_directory(self, directory_path: str) -> None:
        """Stop watching a directory."""
        if directory_path in self.file_watchers:
            observer = self.file_watchers[directory_path]
            observer.stop()
            observer.join()
            
            del self.file_watchers[directory_path]
            self.watched_paths.discard(directory_path)
            
            logger.info(f"Stopped watching directory: {directory_path}")
    
    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get detailed file information."""
        try:
            if not os.path.exists(file_path):
                return None
            
            stat = os.stat(file_path)
            content_hash = self._get_file_hash(file_path)
            
            return {
                "path": file_path,
                "size": stat.st_size,
                "modified_time": stat.st_mtime,
                "created_time": stat.st_ctime,
                "permissions": stat.st_mode,
                "content_hash": content_hash,
                "in_cache": file_path in self.file_cache
            }
        except Exception as e:
            logger.error(f"Error getting file info for {file_path}: {e}")
            return None
    
    def clear_cache(self, file_path: Optional[str] = None) -> None:
        """Clear file cache."""
        if file_path:
            if file_path in self.file_cache:
                del self.file_cache[file_path]
                if file_path in self.cache_access_order:
                    self.cache_access_order.remove(file_path)
        else:
            self.file_cache.clear()
            self.cache_access_order.clear()
        
        logger.info("File cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cache_size": len(self.file_cache),
            "max_cache_size": self.cache_size,
            "cache_hits": self.metrics["cache_hits"],
            "cache_misses": self.metrics["cache_misses"],
            "hit_rate": (self.metrics["cache_hits"] / 
                        (self.metrics["cache_hits"] + self.metrics["cache_misses"])) 
                        if (self.metrics["cache_hits"] + self.metrics["cache_misses"]) > 0 else 0
        }
    
    def rollback_operations(self, operation_ids: List[str]) -> Dict[str, Any]:
        """Rollback specific operations."""
        rollback_results = {
            "successful": [],
            "failed": [],
            "not_found": []
        }
        
        for operation_id in operation_ids:
            # Find operation in history
            operation = None
            for op in reversed(self.operation_history):
                if op.operation_id == operation_id:
                    operation = op
                    break
            
            if not operation:
                rollback_results["not_found"].append(operation_id)
                continue
            
            try:
                self._rollback_operation(operation)
                rollback_results["successful"].append(operation_id)
            except Exception as e:
                logger.error(f"Failed to rollback operation {operation_id}: {e}")
                rollback_results["failed"].append(operation_id)
        
        return rollback_results
    
    def _rollback_operation(self, operation: FileOperation) -> None:
        """Rollback a single operation."""
        if operation.operation_type == "write":
            # Rollback write by deleting the file
            if operation.target_path and os.path.exists(operation.target_path):
                os.remove(operation.target_path)
        
        elif operation.operation_type == "delete":
            # Rollback delete by restoring content
            if operation.target_path and operation.content:
                os.makedirs(os.path.dirname(operation.target_path), exist_ok=True)
                with open(operation.target_path, 'wb') as f:
                    f.write(operation.content)
        
        elif operation.operation_type == "move":
            # Rollback move by moving back
            if operation.source_path and operation.target_path:
                if os.path.exists(operation.target_path):
                    shutil.move(operation.target_path, operation.source_path)
        
        elif operation.operation_type == "copy":
            # Rollback copy by deleting the copy
            if operation.target_path and os.path.exists(operation.target_path):
                os.remove(operation.target_path)
    
    def export_operation_history(self, file_path: str) -> None:
        """Export operation history to file."""
        history_data = []
        for operation in self.operation_history:
            history_data.append({
                "operation_id": operation.operation_id,
                "operation_type": operation.operation_type,
                "source_path": operation.source_path,
                "target_path": operation.target_path,
                "timestamp": operation.timestamp,
                "metadata": operation.metadata
            })
        
        with open(file_path, 'w') as f:
            json.dump(history_data, f, indent=2, default=str)
        
        logger.info(f"Operation history exported to {file_path}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics."""
        return {
            "operations": self.metrics.copy(),
            "cache": self.get_cache_stats(),
            "watching": {
                "watched_paths": len(self.watched_paths),
                "active_watchers": len(self.file_watchers)
            },
            "history": {
                "total_operations": len(self.operation_history),
                "pending_operations": len(self.pending_operations)
            }
        }
    
    def shutdown(self) -> None:
        """Shutdown the file operations manager."""
        # Execute any pending operations
        self._execute_batch()
        
        # Stop all file watchers
        for directory_path in list(self.file_watchers.keys()):
            self.unwatch_directory(directory_path)
        
        # Clear cache
        self.clear_cache()
        
        logger.info("File operations manager shutdown complete")


# Global file operations manager instance
file_operations_manager = FileOperationsManager()
