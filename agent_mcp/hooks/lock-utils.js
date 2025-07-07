#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

class LockUtils {
  constructor(lockDir = '.agent-locks', activityDir = '.agent-activity') {
    this.lockDir = path.resolve(lockDir);
    this.activityDir = path.resolve(activityDir);
    this.defaultTimeout = 10 * 60 * 1000; // 10 minutes
    
    // Ensure directories exist
    this.ensureDirectories();
  }

  ensureDirectories() {
    try {
      if (!fs.existsSync(this.lockDir)) {
        fs.mkdirSync(this.lockDir, { recursive: true });
      }
      if (!fs.existsSync(this.activityDir)) {
        fs.mkdirSync(this.activityDir, { recursive: true });
      }
    } catch (error) {
      console.warn(`Warning: Could not create lock directories: ${error.message}`);
    }
  }

  /**
   * Convert file path to lock file name
   * @param {string} filePath - Original file path
   * @returns {string} Lock file name
   */
  pathToLockName(filePath) {
    // Convert path separators to dashes and remove leading slashes/dots
    return filePath
      .replace(/^\.?\/+/, '') // Remove leading ./ or /
      .replace(/[\/\\]/g, '-') // Replace slashes with dashes
      .replace(/[<>:"|?*]/g, '_') // Replace invalid filename chars
      + '.lock';
  }

  /**
   * Get full path to lock file
   * @param {string} filePath - Original file path
   * @returns {string} Full lock file path
   */
  getLockFilePath(filePath) {
    const lockName = this.pathToLockName(filePath);
    return path.join(this.lockDir, lockName);
  }

  /**
   * Check if file is currently locked
   * @param {string} filePath - File to check
   * @returns {Object|null} Lock info or null if not locked
   */
  isLocked(filePath) {
    const lockFilePath = this.getLockFilePath(filePath);
    
    try {
      if (!fs.existsSync(lockFilePath)) {
        return null;
      }

      const lockData = JSON.parse(fs.readFileSync(lockFilePath, 'utf8'));
      
      // Check if lock has expired
      const now = new Date();
      const expiresAt = new Date(lockData.expires_at);
      
      if (now > expiresAt) {
        // Lock expired, remove it
        this.releaseLock(filePath);
        return null;
      }

      return lockData;
    } catch (error) {
      console.warn(`Warning: Error checking lock for ${filePath}: ${error.message}`);
      return null;
    }
  }

  /**
   * Create a lock for the specified file
   * @param {string} filePath - File to lock
   * @param {string} agentId - Agent creating the lock
   * @param {string} operation - Operation type (editing, writing, etc)
   * @param {string} sessionId - Session ID
   * @param {number} timeout - Lock timeout in milliseconds
   * @returns {boolean} True if lock created successfully
   */
  createLock(filePath, agentId, operation = 'editing', sessionId = 'unknown', timeout = null) {
    const lockFilePath = this.getLockFilePath(filePath);
    timeout = timeout || this.defaultTimeout;
    
    try {
      // Check if already locked
      const existingLock = this.isLocked(filePath);
      if (existingLock && existingLock.agent_id !== agentId) {
        return false; // Already locked by different agent
      }

      const now = new Date();
      const expiresAt = new Date(now.getTime() + timeout);
      
      const lockData = {
        agent_id: agentId,
        file_path: filePath,
        locked_at: now.toISOString(),
        operation: operation,
        session_id: sessionId,
        expires_at: expiresAt.toISOString(),
        lock_id: crypto.randomUUID()
      };

      // Atomic write using temporary file
      const tempPath = lockFilePath + '.tmp';
      fs.writeFileSync(tempPath, JSON.stringify(lockData, null, 2));
      fs.renameSync(tempPath, lockFilePath);

      this.logActivity('lock_created', agentId, filePath, { operation, session_id: sessionId });
      return true;
    } catch (error) {
      console.warn(`Warning: Could not create lock for ${filePath}: ${error.message}`);
      return false;
    }
  }

  /**
   * Release a lock for the specified file
   * @param {string} filePath - File to unlock
   * @param {string} agentId - Agent releasing the lock (optional, for verification)
   * @returns {boolean} True if lock released successfully
   */
  releaseLock(filePath, agentId = null) {
    const lockFilePath = this.getLockFilePath(filePath);
    
    try {
      if (!fs.existsSync(lockFilePath)) {
        return true; // Already unlocked
      }

      // If agentId provided, verify ownership
      if (agentId) {
        const lockData = JSON.parse(fs.readFileSync(lockFilePath, 'utf8'));
        if (lockData.agent_id !== agentId) {
          console.warn(`Warning: Agent ${agentId} tried to release lock owned by ${lockData.agent_id}`);
          return false;
        }
      }

      fs.unlinkSync(lockFilePath);
      this.logActivity('lock_released', agentId, filePath, {});
      return true;
    } catch (error) {
      console.warn(`Warning: Could not release lock for ${filePath}: ${error.message}`);
      return false;
    }
  }

  /**
   * Release all locks held by a specific agent
   * @param {string} agentId - Agent whose locks to release
   * @returns {number} Number of locks released
   */
  releaseAllLocks(agentId) {
    let released = 0;
    
    try {
      const lockFiles = fs.readdirSync(this.lockDir);
      
      for (const lockFile of lockFiles) {
        if (!lockFile.endsWith('.lock')) continue;
        
        const lockFilePath = path.join(this.lockDir, lockFile);
        try {
          const lockData = JSON.parse(fs.readFileSync(lockFilePath, 'utf8'));
          if (lockData.agent_id === agentId) {
            fs.unlinkSync(lockFilePath);
            this.logActivity('lock_released', agentId, lockData.file_path, { reason: 'agent_cleanup' });
            released++;
          }
        } catch (error) {
          console.warn(`Warning: Error processing lock file ${lockFile}: ${error.message}`);
        }
      }
    } catch (error) {
      console.warn(`Warning: Error releasing locks for agent ${agentId}: ${error.message}`);
    }

    return released;
  }

  /**
   * Get all current locks
   * @returns {Array} Array of lock objects
   */
  getAllLocks() {
    const locks = [];
    
    try {
      const lockFiles = fs.readdirSync(this.lockDir);
      
      for (const lockFile of lockFiles) {
        if (!lockFile.endsWith('.lock')) continue;
        
        const lockFilePath = path.join(this.lockDir, lockFile);
        try {
          const lockData = JSON.parse(fs.readFileSync(lockFilePath, 'utf8'));
          
          // Check if expired
          const now = new Date();
          const expiresAt = new Date(lockData.expires_at);
          
          if (now > expiresAt) {
            // Clean up expired lock
            fs.unlinkSync(lockFilePath);
            continue;
          }
          
          locks.push(lockData);
        } catch (error) {
          console.warn(`Warning: Error reading lock file ${lockFile}: ${error.message}`);
        }
      }
    } catch (error) {
      console.warn(`Warning: Error getting all locks: ${error.message}`);
    }

    return locks;
  }

  /**
   * Log activity to the activity feed
   * @param {string} action - Action type
   * @param {string} agentId - Agent ID
   * @param {string} filePath - File path
   * @param {Object} details - Additional details
   */
  logActivity(action, agentId, filePath, details = {}) {
    try {
      const activityFile = path.join(this.activityDir, 'live-feed.jsonl');
      const entry = {
        timestamp: new Date().toISOString(),
        action: action,
        agent_id: agentId,
        file_path: filePath,
        ...details
      };
      
      fs.appendFileSync(activityFile, JSON.stringify(entry) + '\n');
    } catch (error) {
      console.warn(`Warning: Could not log activity: ${error.message}`);
    }
  }

  /**
   * Clean up expired locks
   * @returns {number} Number of locks cleaned up
   */
  cleanupExpiredLocks() {
    let cleaned = 0;
    
    try {
      const lockFiles = fs.readdirSync(this.lockDir);
      const now = new Date();
      
      for (const lockFile of lockFiles) {
        if (!lockFile.endsWith('.lock')) continue;
        
        const lockFilePath = path.join(this.lockDir, lockFile);
        try {
          const lockData = JSON.parse(fs.readFileSync(lockFilePath, 'utf8'));
          const expiresAt = new Date(lockData.expires_at);
          
          if (now > expiresAt) {
            fs.unlinkSync(lockFilePath);
            this.logActivity('lock_expired', lockData.agent_id, lockData.file_path, {});
            cleaned++;
          }
        } catch (error) {
          console.warn(`Warning: Error processing lock file ${lockFile}: ${error.message}`);
        }
      }
    } catch (error) {
      console.warn(`Warning: Error cleaning up expired locks: ${error.message}`);
    }

    return cleaned;
  }
}

module.exports = LockUtils;