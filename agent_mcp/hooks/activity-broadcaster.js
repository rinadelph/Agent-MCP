#!/usr/bin/env node

const LockUtils = require('./lock-utils');
const fs = require('fs');
const path = require('path');

/**
 * Activity Broadcaster Hook for Claude Code PostToolUse
 * 
 * This hook logs completed file operations for real-time visibility
 * and releases file locks after successful operations.
 */
class ActivityBroadcaster {
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
    return process.env.MCP_AGENT_ID || 
           input.agent_id ||
           input.session_id ||
           'unknown-agent';
  }

  /**
   * Analyze tool response for additional details
   * @param {Object} toolResponse - Tool response object
   * @returns {Object} Analysis details
   */
  analyzeToolResponse(toolResponse) {
    const details = {};
    
    if (toolResponse) {
      // Extract success status
      details.success = toolResponse.success !== false;
      
      // Extract any error information
      if (toolResponse.error) {
        details.error = toolResponse.error;
      }
      
      // Extract file information if available
      if (toolResponse.filePath) {
        details.actual_file_path = toolResponse.filePath;
      }
      
      // Extract content length for write operations
      if (toolResponse.content && typeof toolResponse.content === 'string') {
        details.content_length = toolResponse.content.length;
        details.lines_written = toolResponse.content.split('\n').length;
      }
    }
    
    return details;
  }

  /**
   * Get file statistics
   * @param {string} filePath - File path
   * @returns {Object} File statistics
   */
  getFileStats(filePath) {
    try {
      if (fs.existsSync(filePath)) {
        const stats = fs.statSync(filePath);
        const content = fs.readFileSync(filePath, 'utf8');
        
        return {
          size_bytes: stats.size,
          modified_at: stats.mtime.toISOString(),
          lines_total: content.split('\n').length,
          file_exists: true
        };
      } else {
        return {
          file_exists: false
        };
      }
    } catch (error) {
      return {
        file_exists: false,
        stat_error: error.message
      };
    }
  }

  /**
   * Update agent status
   * @param {string} agentId - Agent ID
   * @param {string} status - Current status
   * @param {Object} details - Additional details
   */
  updateAgentStatus(agentId, status, details = {}) {
    try {
      const statusFile = path.join(this.lockUtils.activityDir, 'agent-status.json');
      let agentStatuses = {};
      
      // Load existing statuses
      if (fs.existsSync(statusFile)) {
        try {
          agentStatuses = JSON.parse(fs.readFileSync(statusFile, 'utf8'));
        } catch (error) {
          console.warn(`Warning: Could not parse agent status file: ${error.message}`);
        }
      }
      
      // Update status for this agent
      agentStatuses[agentId] = {
        status: status,
        last_activity: new Date().toISOString(),
        ...details
      };
      
      // Write back to file
      fs.writeFileSync(statusFile, JSON.stringify(agentStatuses, null, 2));
    } catch (error) {
      console.warn(`Warning: Could not update agent status: ${error.message}`);
    }
  }

  /**
   * Log detailed activity information
   * @param {Object} activityData - Activity data to log
   */
  logDetailedActivity(activityData) {
    try {
      const activityFile = path.join(this.lockUtils.activityDir, 'live-feed.jsonl');
      const entry = {
        timestamp: new Date().toISOString(),
        ...activityData
      };
      
      fs.appendFileSync(activityFile, JSON.stringify(entry) + '\n');
    } catch (error) {
      console.warn(`Warning: Could not log detailed activity: ${error.message}`);
    }
  }

  /**
   * Check if file should be excluded from activity logging
   * @param {string} filePath - File path to check
   * @returns {boolean} True if should be excluded
   */
  shouldExcludeFile(filePath) {
    const excludePatterns = [
      /\.log$/,
      /\.tmp$/,
      /\.temp$/,
      /\.lock$/,
      /\.agent-/,
      /\.git\//,
      /node_modules\//
    ];

    return excludePatterns.some(pattern => pattern.test(filePath));
  }

  /**
   * Main execution logic
   * @param {Object} input - Hook input from Claude Code
   * @returns {Object} Hook response
   */
  async execute(input) {
    try {
      const { tool_name, tool_input, tool_response, session_id } = input;
      
      // Handle all tool operations for visibility
      const filePath = this.extractFilePath(tool_input);
      const agentId = this.extractAgentId(input);
      
      // Basic activity logging for all operations
      const baseActivity = {
        action: 'tool_completed',
        agent_id: agentId,
        tool_name: tool_name,
        session_id: session_id,
        file_path: filePath
      };

      // If it's a file operation, add detailed information
      if (filePath && !this.shouldExcludeFile(filePath)) {
        const responseDetails = this.analyzeToolResponse(tool_response);
        const fileStats = this.getFileStats(filePath);
        
        const detailedActivity = {
          ...baseActivity,
          response_details: responseDetails,
          file_stats: fileStats,
          operation_successful: responseDetails.success !== false
        };

        this.logDetailedActivity(detailedActivity);

        // Release file lock for modification operations
        if (['Edit', 'Write', 'MultiEdit'].includes(tool_name)) {
          const lockReleased = this.lockUtils.releaseLock(filePath, agentId);
          
          if (lockReleased) {
            this.logDetailedActivity({
              action: 'lock_released',
              agent_id: agentId,
              file_path: filePath,
              reason: 'operation_completed',
              tool_name: tool_name
            });
          }

          // Update agent status
          this.updateAgentStatus(agentId, 'idle', {
            last_file: filePath,
            last_operation: tool_name.toLowerCase(),
            operations_completed: (input.operations_completed || 0) + 1
          });
        }
      } else {
        // Log non-file operations too for complete visibility
        this.logDetailedActivity(baseActivity);
      }

      // Update agent status for all operations
      this.updateAgentStatus(agentId, 'active', {
        last_tool: tool_name,
        last_activity_detail: filePath ? `${tool_name} on ${path.basename(filePath)}` : tool_name
      });

      // Always return success for PostToolUse hooks
      return {
        success: true,
        message: `Activity logged for ${tool_name}${filePath ? ` on ${path.basename(filePath)}` : ''}`,
        agent_id: agentId
      };

    } catch (error) {
      console.error(`Activity broadcaster error: ${error.message}`);
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Output result to stdout
   * @param {Object} result - Hook result
   */
  outputResult(result) {
    // PostToolUse hooks don't block operations, just log results
    if (result.success) {
      // Output success message to stdout for transcript
      if (result.message) {
        console.log(result.message);
      }
      process.exit(0);
    } else {
      // Output error to stderr but don't block
      console.error(`Activity logging failed: ${result.error}`);
      process.exit(1);
    }
  }
}

// CLI execution
if (require.main === module) {
  (async () => {
    try {
      const broadcaster = new ActivityBroadcaster();
      const input = await broadcaster.parseInput();
      const result = await broadcaster.execute(input);
      broadcaster.outputResult(result);
    } catch (error) {
      console.error(`Activity broadcaster error: ${error.message}`);
      process.exit(1);
    }
  })();
}

module.exports = ActivityBroadcaster;