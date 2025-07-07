#!/usr/bin/env node

const LockUtils = require('./lock-utils');
const path = require('path');

/**
 * Lock cleanup utility for administrative tasks
 */
class LockCleanup {
  constructor() {
    this.lockUtils = new LockUtils();
  }

  /**
   * Display current lock status
   */
  showStatus() {
    console.log('=== Agent File Lock Status ===\n');
    
    const locks = this.lockUtils.getAllLocks();
    
    if (locks.length === 0) {
      console.log('No active file locks.');
      return;
    }

    console.log(`Found ${locks.length} active lock(s):\n`);
    
    locks.forEach((lock, index) => {
      const timeRemaining = Math.ceil((new Date(lock.expires_at) - new Date()) / 1000 / 60);
      console.log(`${index + 1}. File: ${lock.file_path}`);
      console.log(`   Agent: ${lock.agent_id}`);
      console.log(`   Operation: ${lock.operation}`);
      console.log(`   Locked: ${new Date(lock.locked_at).toLocaleString()}`);
      console.log(`   Expires: ${timeRemaining} minutes`);
      console.log(`   Session: ${lock.session_id}`);
      console.log('');
    });
  }

  /**
   * Clean up expired locks
   */
  cleanExpired() {
    console.log('Cleaning up expired locks...');
    const cleaned = this.lockUtils.cleanupExpiredLocks();
    console.log(`Cleaned up ${cleaned} expired lock(s).`);
  }

  /**
   * Release all locks for a specific agent
   * @param {string} agentId - Agent ID
   */
  releaseAgent(agentId) {
    console.log(`Releasing all locks for agent: ${agentId}`);
    const released = this.lockUtils.releaseAllLocks(agentId);
    console.log(`Released ${released} lock(s) for agent ${agentId}.`);
  }

  /**
   * Force release a specific file lock
   * @param {string} filePath - File path to unlock
   */
  forceRelease(filePath) {
    console.log(`Force releasing lock for file: ${filePath}`);
    const released = this.lockUtils.releaseLock(filePath);
    if (released) {
      console.log(`Successfully released lock for ${filePath}.`);
    } else {
      console.log(`No lock found for ${filePath} or release failed.`);
    }
  }

  /**
   * Show help information
   */
  showHelp() {
    console.log('Agent File Lock Management Utility\n');
    console.log('Usage: node cleanup-locks.js <command> [options]\n');
    console.log('Commands:');
    console.log('  status                    Show current lock status');
    console.log('  clean                     Clean up expired locks');
    console.log('  release-agent <agent_id>  Release all locks for an agent');
    console.log('  force-release <file_path> Force release lock for a file');
    console.log('  help                      Show this help message\n');
    console.log('Examples:');
    console.log('  node cleanup-locks.js status');
    console.log('  node cleanup-locks.js clean');
    console.log('  node cleanup-locks.js release-agent worker1');
    console.log('  node cleanup-locks.js force-release src/main.py');
  }
}

// CLI execution
if (require.main === module) {
  const cleanup = new LockCleanup();
  const args = process.argv.slice(2);
  
  if (args.length === 0) {
    cleanup.showHelp();
    process.exit(0);
  }

  const command = args[0];
  
  try {
    switch (command) {
      case 'status':
        cleanup.showStatus();
        break;
        
      case 'clean':
        cleanup.cleanExpired();
        break;
        
      case 'release-agent':
        if (args.length < 2) {
          console.error('Error: Agent ID required for release-agent command');
          process.exit(1);
        }
        cleanup.releaseAgent(args[1]);
        break;
        
      case 'force-release':
        if (args.length < 2) {
          console.error('Error: File path required for force-release command');
          process.exit(1);
        }
        cleanup.forceRelease(args[1]);
        break;
        
      case 'help':
        cleanup.showHelp();
        break;
        
      default:
        console.error(`Error: Unknown command '${command}'`);
        cleanup.showHelp();
        process.exit(1);
    }
  } catch (error) {
    console.error(`Error: ${error.message}`);
    process.exit(1);
  }
}

module.exports = LockCleanup;