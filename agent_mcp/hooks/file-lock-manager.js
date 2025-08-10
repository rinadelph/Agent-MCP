#!/usr/bin/env node

const LockUtils = require('./lock-utils');

/**
 * File Lock Manager Hook for Claude Code PreToolUse
 * 
 * This hook intercepts Edit/Write/MultiEdit operations to prevent file conflicts
 * through a file-level locking mechanism.
 */
class FileLockManager {
  constructor() {
    this.lockUtils = new LockUtils();
  }

  /**
   * Parse input from Claude Code hook
   * @returns {Promise<Object>} Parsed hook input
   */
  async parseInput() {
    return new Promise((resolve, reject) => {
      let input = '';
      
      process.stdin.on('data', (chunk) => {
        input += chunk.toString();
      });
      
      process.stdin.on('end', () => {
        try {
          const data = JSON.parse(input);
          resolve(data);
        } catch (error) {
          reject(new Error(`Invalid JSON input: ${error.message}`));
        }
      });
      
      process.stdin.on('error', reject);
    });
  }

  /**
   * Extract file path from tool input
   * @param {Object} toolInput - Tool input object
   * @returns {string|null} File path or null if not found
   */
  extractFilePath(toolInput) {
    // Handle different tool input formats
    return toolInput.file_path || 
           toolInput.filePath ||
           (toolInput.edits && toolInput.edits[0] && toolInput.edits[0].file_path) ||
           null;
  }

  /**
   * Extract agent ID from hook input
   * @param {Object} input - Hook input
   * @returns {string} Agent ID
   */
  extractAgentId(input) {
    // Try various ways to extract agent ID
    return process.env.MCP_AGENT_ID || 
           input.agent_id ||
           input.session_id ||
           'unknown-agent';
  }

  /**
   * Determine operation type from tool name
   * @param {string} toolName - Claude Code tool name
   * @returns {string} Operation type
   */
  getOperationType(toolName) {
    switch (toolName) {
      case 'Edit':
      case 'MultiEdit':
        return 'editing';
      case 'Write':
        return 'writing';
      default:
        return 'modifying';
    }
  }

  /**
   * Check if file should be excluded from locking
   * @param {string} filePath - File path to check
   * @returns {boolean} True if should be excluded
   */
  shouldExcludeFile(filePath) {
    const excludePatterns = [
      /\.log$/,
      /\.tmp$/,
      /\.temp$/,
      /\.lock$/,
      /\.env/,
      /\.git\//,
      /\.agent-/,
      /node_modules\//,
      /\.pyc$/,
      /__pycache__\//
    ];

    return excludePatterns.some(pattern => pattern.test(filePath));
  }

  /**
   * Generate hook response
   * @param {string} decision - 'approve', 'block', or undefined
   * @param {string} reason - Reason for the decision
   * @param {Object} additionalData - Additional response data
   * @returns {Object} Hook response
   */
  generateResponse(decision, reason = null, additionalData = {}) {
    const response = {
      ...additionalData
    };

    if (decision) {
      response.decision = decision;
    }
    
    if (reason) {
      response.reason = reason;
    }

    return response;
  }

  /**
   * Main execution logic
   * @param {Object} input - Hook input from Claude Code
   * @returns {Object} Hook response
   */
  async execute(input) {
    try {
      const { tool_name, tool_input, session_id } = input;
      
      // Only handle file modification tools
      if (!['Edit', 'Write', 'MultiEdit'].includes(tool_name)) {
        return this.generateResponse(); // Allow other tools
      }

      const filePath = this.extractFilePath(tool_input);
      if (!filePath) {
        return this.generateResponse(); // No file path, allow operation
      }

      // Check if file should be excluded from locking
      if (this.shouldExcludeFile(filePath)) {
        return this.generateResponse(); // Excluded file, allow operation
      }

      const agentId = this.extractAgentId(input);
      const operation = this.getOperationType(tool_name);

      // Clean up any expired locks first
      this.lockUtils.cleanupExpiredLocks();

      // Check if file is currently locked
      const existingLock = this.lockUtils.isLocked(filePath);
      
      if (existingLock) {
        if (existingLock.agent_id === agentId) {
          // Same agent already has the lock, allow operation
          return this.generateResponse('approve', `File already locked by this agent`);
        } else {
          // File locked by different agent, block operation
          const timeRemaining = Math.ceil((new Date(existingLock.expires_at) - new Date()) / 1000 / 60);
          return this.generateResponse(
            'block', 
            `File "${filePath}" is currently being ${existingLock.operation} by agent "${existingLock.agent_id}". Lock expires in ${timeRemaining} minutes. Please wait or work on a different file.`
          );
        }
      }

      // File is not locked, create lock and approve operation
      const lockCreated = this.lockUtils.createLock(filePath, agentId, operation, session_id);
      
      if (lockCreated) {
        return this.generateResponse(
          'approve', 
          `File lock acquired for "${filePath}"`
        );
      } else {
        // Lock creation failed, allow operation with warning
        return this.generateResponse(
          undefined,
          `Warning: Could not create file lock for "${filePath}", proceeding without lock protection`
        );
      }

    } catch (error) {
      // Log error but don't block operation
      console.error(`File lock manager error: ${error.message}`);
      return this.generateResponse(
        undefined,
        `Warning: File lock check failed (${error.message}), proceeding without lock protection`
      );
    }
  }

  /**
   * Output result to stdout/stderr based on hook protocol
   * @param {Object} result - Hook result
   */
  outputResult(result) {
    if (result.decision === 'block') {
      // Blocking result - output reason to stderr and exit with code 2
      console.error(result.reason);
      process.exit(2);
    } else if (result.decision === 'approve') {
      // Approval result - output JSON to stdout
      console.log(JSON.stringify(result));
      process.exit(0);
    } else {
      // Allow operation - output any reason to stdout if present
      if (result.reason) {
        console.log(result.reason);
      }
      process.exit(0);
    }
  }
}

// CLI execution
if (require.main === module) {
  (async () => {
    try {
      const manager = new FileLockManager();
      const input = await manager.parseInput();
      const result = await manager.execute(input);
      manager.outputResult(result);
    } catch (error) {
      console.error(`File lock manager error: ${error.message}`);
      process.exit(1);
    }
  })();
}

module.exports = FileLockManager;