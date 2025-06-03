"""Migration lock mechanism to prevent concurrent migrations"""
import os
import sys
import time
import tempfile
from pathlib import Path
from contextlib import contextmanager
from typing import Optional

from ...core.config import logger, get_db_path

# Platform-specific imports
if sys.platform != 'win32':
    import fcntl
else:
    fcntl = None


class MigrationLock:
    """File-based lock to prevent concurrent migrations"""
    
    def __init__(self, lock_file: Optional[Path] = None):
        if lock_file is None:
            db_path = get_db_path()
            self.lock_file = db_path.parent / ".migration.lock"
        else:
            self.lock_file = lock_file
        
        self.lock_fd = None
        self.is_locked = False
    
    def acquire(self, timeout: float = 60.0) -> bool:
        """
        Try to acquire the migration lock.
        
        Args:
            timeout: Maximum time to wait for the lock in seconds
            
        Returns:
            True if lock acquired, False if timeout
        """
        start_time = time.time()
        
        # Ensure lock directory exists
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        
        while True:
            try:
                if fcntl is not None:
                    # Unix-like systems: use fcntl
                    # Open or create the lock file
                    self.lock_fd = open(self.lock_file, 'w')
                    
                    # Try to acquire exclusive lock (non-blocking)
                    fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    
                    # Write PID and timestamp to lock file
                    self.lock_fd.write(f"{os.getpid()}\n{time.time()}\n")
                    self.lock_fd.flush()
                    
                    self.is_locked = True
                    logger.info(f"Acquired migration lock (PID: {os.getpid()})")
                    return True
                else:
                    # Windows: use exclusive file opening
                    try:
                        # Try to open file exclusively
                        self.lock_fd = open(self.lock_file, 'x')
                        # Write PID and timestamp to lock file
                        self.lock_fd.write(f"{os.getpid()}\n{time.time()}\n")
                        self.lock_fd.flush()
                        self.lock_fd.close()
                        
                        # Re-open in write mode for consistency
                        self.lock_fd = open(self.lock_file, 'w')
                        self.lock_fd.write(f"{os.getpid()}\n{time.time()}\n")
                        self.lock_fd.flush()
                        
                        self.is_locked = True
                        logger.info(f"Acquired migration lock (PID: {os.getpid()})")
                        return True
                    except FileExistsError:
                        # Lock file exists, check if stale
                        if self._is_lock_stale():
                            logger.warning("Detected stale migration lock, removing...")
                            try:
                                self.lock_file.unlink()
                            except:
                                pass
                        else:
                            # Lock is held by another process
                            pass
                
            except IOError:
                # Lock is held by another process
                if self.lock_fd:
                    self.lock_fd.close()
                    self.lock_fd = None
                
                # Check if we've exceeded timeout
                if time.time() - start_time > timeout:
                    logger.error(f"Failed to acquire migration lock after {timeout}s")
                    return False
                
                # Check if lock is stale
                if self._is_lock_stale():
                    logger.warning("Detected stale migration lock, removing...")
                    try:
                        self.lock_file.unlink()
                    except:
                        pass
                else:
                    logger.info("Waiting for migration lock...")
                
                # Wait before retrying
                time.sleep(1.0)
    
    def release(self):
        """Release the migration lock"""
        if self.lock_fd and self.is_locked:
            try:
                if fcntl is not None:
                    # Release the lock on Unix-like systems
                    fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_UN)
                
                self.lock_fd.close()
                
                # Remove the lock file
                if self.lock_file.exists():
                    self.lock_file.unlink()
                
                logger.info("Released migration lock")
            except Exception as e:
                logger.warning(f"Error releasing migration lock: {e}")
            finally:
                self.lock_fd = None
                self.is_locked = False
    
    def _is_lock_stale(self, stale_threshold: float = 300.0) -> bool:
        """
        Check if the lock file is stale (older than threshold).
        
        Args:
            stale_threshold: Time in seconds after which lock is considered stale
            
        Returns:
            True if lock is stale, False otherwise
        """
        try:
            if not self.lock_file.exists():
                return False
            
            # Read lock file content
            with open(self.lock_file, 'r') as f:
                lines = f.readlines()
            
            if len(lines) >= 2:
                # Check timestamp
                lock_time = float(lines[1].strip())
                if time.time() - lock_time > stale_threshold:
                    return True
                
                # Check if process is still alive
                pid = int(lines[0].strip())
                try:
                    # Send signal 0 to check if process exists
                    os.kill(pid, 0)
                    return False
                except ProcessLookupError:
                    # Process doesn't exist
                    return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking lock staleness: {e}")
            return False
    
    def __enter__(self):
        """Context manager entry"""
        if not self.acquire():
            raise RuntimeError("Failed to acquire migration lock")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release()


@contextmanager
def migration_lock(timeout: float = 60.0):
    """
    Context manager for migration locking.
    
    Usage:
        with migration_lock():
            # Run migration
            pass
    """
    lock = MigrationLock()
    try:
        if not lock.acquire(timeout):
            raise RuntimeError("Failed to acquire migration lock")
        yield lock
    finally:
        lock.release()