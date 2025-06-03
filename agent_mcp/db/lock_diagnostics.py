"""Database lock diagnostics utilities"""
import sqlite3
import os
import subprocess
import platform
from pathlib import Path
from typing import Optional, List, Dict, Any

from ..core.config import logger, get_db_path


def get_database_lock_info() -> Dict[str, Any]:
    """
    Get information about which processes have the database file open.
    
    Returns:
        Dictionary with lock information
    """
    db_path = get_db_path()
    lock_info = {
        'database_path': str(db_path),
        'exists': db_path.exists(),
        'processes': []
    }
    
    if not db_path.exists():
        return lock_info
    
    system = platform.system()
    
    try:
        if system == 'Linux':
            # Use lsof to find processes with the database file open
            cmd = ['lsof', str(db_path)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 2:
                        lock_info['processes'].append({
                            'command': parts[0],
                            'pid': parts[1],
                            'user': parts[2] if len(parts) > 2 else 'unknown',
                            'full_line': line
                        })
        elif system == 'Darwin':  # macOS
            # Similar to Linux
            cmd = ['lsof', str(db_path)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 2:
                        lock_info['processes'].append({
                            'command': parts[0],
                            'pid': parts[1],
                            'user': parts[2] if len(parts) > 2 else 'unknown',
                            'full_line': line
                        })
        elif system == 'Windows':
            # Use handle.exe or similar if available
            # For now, just indicate Windows doesn't have easy lock detection
            lock_info['note'] = 'Process lock detection not implemented for Windows'
    except Exception as e:
        lock_info['error'] = str(e)
        logger.debug(f"Error getting lock info: {e}")
    
    # Check for WAL files
    wal_path = Path(str(db_path) + '-wal')
    shm_path = Path(str(db_path) + '-shm')
    journal_path = Path(str(db_path) + '-journal')
    
    lock_info['wal_exists'] = wal_path.exists()
    lock_info['shm_exists'] = shm_path.exists()
    lock_info['journal_exists'] = journal_path.exists()
    
    if wal_path.exists():
        lock_info['wal_size'] = wal_path.stat().st_size
    if shm_path.exists():
        lock_info['shm_size'] = shm_path.stat().st_size
    if journal_path.exists():
        lock_info['journal_size'] = journal_path.stat().st_size
        logger.warning("[LOCK DIAGNOSTICS] Found SQLite journal file - indicates uncommitted transaction!")
    
    return lock_info


def log_database_lock_diagnostics():
    """Log detailed diagnostics about database locks"""
    logger.info("[LOCK DIAGNOSTICS] Checking database lock status...")
    
    lock_info = get_database_lock_info()
    
    logger.info(f"[LOCK DIAGNOSTICS] Database: {lock_info['database_path']}")
    logger.info(f"[LOCK DIAGNOSTICS] Exists: {lock_info['exists']}")
    logger.info(f"[LOCK DIAGNOSTICS] WAL exists: {lock_info.get('wal_exists', False)}")
    logger.info(f"[LOCK DIAGNOSTICS] SHM exists: {lock_info.get('shm_exists', False)}")
    
    if lock_info.get('wal_size'):
        logger.info(f"[LOCK DIAGNOSTICS] WAL size: {lock_info['wal_size']} bytes")
    
    if lock_info['processes']:
        logger.warning(f"[LOCK DIAGNOSTICS] Found {len(lock_info['processes'])} processes with database open:")
        for proc in lock_info['processes']:
            logger.warning(f"[LOCK DIAGNOSTICS]   - {proc['command']} (PID: {proc['pid']}, User: {proc['user']})")
    else:
        logger.info("[LOCK DIAGNOSTICS] No processes found with database file open (via lsof)")
    
    if 'error' in lock_info:
        logger.error(f"[LOCK DIAGNOSTICS] Error: {lock_info['error']}")
    
    if 'note' in lock_info:
        logger.info(f"[LOCK DIAGNOSTICS] Note: {lock_info['note']}")
    
    # Try to get SQLite's internal lock state
    try:
        conn = sqlite3.connect(str(get_db_path()), timeout=0.1)
        cursor = conn.cursor()
        
        # Check pragma values
        cursor.execute("PRAGMA journal_mode")
        journal_mode = cursor.fetchone()[0]
        logger.info(f"[LOCK DIAGNOSTICS] Journal mode: {journal_mode}")
        
        cursor.execute("PRAGMA locking_mode")
        locking_mode = cursor.fetchone()[0]
        logger.info(f"[LOCK DIAGNOSTICS] Locking mode: {locking_mode}")
        
        # Try to get lock info (this might fail if locked)
        try:
            cursor.execute("PRAGMA lock_status")
            lock_status = cursor.fetchall()
            logger.info(f"[LOCK DIAGNOSTICS] Lock status: {lock_status}")
        except:
            logger.info("[LOCK DIAGNOSTICS] Could not get lock_status pragma")
        
        conn.close()
        logger.info("[LOCK DIAGNOSTICS] Successfully opened and closed test connection")
        
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            logger.error("[LOCK DIAGNOSTICS] Database is LOCKED - could not open test connection")
        else:
            logger.error(f"[LOCK DIAGNOSTICS] Database error: {e}")
    except Exception as e:
        logger.error(f"[LOCK DIAGNOSTICS] Unexpected error: {e}")
    
    return lock_info