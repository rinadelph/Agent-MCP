# Agent Sandbox Implementation Plan
## File-Level Locking System with Real-Time Visibility

### Overview

This document outlines the implementation of a sophisticated agent sandbox system that provides:
- **Real-time visibility** into agent activities for verification and oversight
- **Perfect conflict prevention** via file-level locking mechanisms
- **Shared collaboration** on main branch with individual auditable sandboxes
- **Zero admin overhead** through automated Claude Code hooks

### Current Problem

The existing worktree system attempts to isolate agents in separate Git branches, which creates:
- Merge conflicts when agents work on similar files
- Lack of real-time visibility into agent activities  
- Complex branch management and coordination overhead
- Race conditions and synchronization issues

### Proposed Solution: Claude Code Hooks-Based File Locking

Instead of Git branch isolation, we implement a file-level locking system using Claude Code hooks that intercepts all file operations and manages access control automatically.

## Architecture Overview

```
Project Structure:
├── .agent-locks/              # File locking system
│   ├── src-main.py.lock      # Lock files (path-based naming)
│   ├── src-utils.js.lock     
│   └── components-app.tsx.lock
├── .agent-activity/           # Real-time activity tracking
│   ├── live-feed.jsonl       # Real-time activity stream
│   ├── agent-status.json     # Current agent states
│   └── lock-history.jsonl    # Lock acquisition/release history
├── agents/                    # Agent sandbox directories
│   ├── agent-worker1/        # Individual worktree (main branch)
│   ├── agent-worker2/        # Individual worktree (main branch)
│   └── agent-admin/          # Individual worktree (main branch)
└── [project files]           # Shared main branch files
```

## Core Components

### 1. File Lock Manager Hook (PreToolUse)

**Purpose**: Intercept Edit/Write/MultiEdit operations to prevent file conflicts

**Hook Configuration**:
```json
{
  "PreToolUse": [{
    "matcher": "Edit|Write|MultiEdit",
    "hooks": [{
      "type": "command",
      "command": "node /agent_mcp/hooks/file-lock-manager.js"
    }]
  }]
}
```

**Behavior**:
- Receives tool input with file path
- Checks if file is locked by another agent
- If locked: Returns `{decision: "block", reason: "File locked by agent-X"}`
- If free: Creates lock file and returns `{decision: "approve"}`
- Handles lock timeouts and cleanup

**Lock File Format**:
```json
{
  "agent_id": "worker1",
  "file_path": "src/main.py", 
  "locked_at": "2025-01-07T10:30:00Z",
  "operation": "editing",
  "session_id": "abc123",
  "expires_at": "2025-01-07T10:40:00Z"
}
```

### 2. Activity Broadcaster Hook (PostToolUse)

**Purpose**: Broadcast completed file operations for real-time visibility

**Hook Configuration**:
```json
{
  "PostToolUse": [{
    "matcher": "Edit|Write|MultiEdit|Read",
    "hooks": [{
      "type": "command", 
      "command": "node /agent_mcp/hooks/activity-broadcaster.js"
    }]
  }]
}
```

**Behavior**:
- Logs completed operations to activity feed
- Updates agent status tracking
- Releases file locks after successful operations
- Broadcasts activity for real-time dashboard

**Activity Feed Format**:
```json
{
  "timestamp": "2025-01-07T10:30:15Z",
  "agent_id": "worker1",
  "operation": "Write",
  "file_path": "src/main.py",
  "session_id": "abc123",
  "status": "completed",
  "details": {
    "lines_modified": 15,
    "lock_duration_ms": 45000
  }
}
```

### 3. Lock Management System

**Lock Directory Structure**:
- `.agent-locks/`: Contains active lock files
- Lock file naming: `{path-with-slashes-as-dashes}.lock`
- Example: `src/main.py` → `src-main.py.lock`

**Lock Lifecycle**:
1. **Acquisition**: Agent requests file edit → Hook creates lock file
2. **Active**: Lock prevents other agents from editing same file
3. **Release**: Operation completes → Hook removes lock file
4. **Timeout**: Lock expires after 10 minutes → Automatic cleanup
5. **Cleanup**: Agent termination → All locks released

**Lock Timeout Handling**:
- Default timeout: 10 minutes
- Configurable per operation type
- Automatic cleanup via background process
- Admin override capability for stuck locks

### 4. Agent Sandbox System

**Worktree Structure**:
- Each agent gets individual worktree directory: `agents/agent-{id}/`
- All agents work on **main branch** (no isolation)
- Changes immediately visible to other agents
- Individual directories provide audit trail and organization

**Benefits of Main Branch Approach**:
- ✅ Real-time collaboration and visibility
- ✅ No merge conflicts (prevented by file locking)
- ✅ Immediate sharing of completed work
- ✅ Simple Git history without complex branching

## Implementation Details

### Phase 1: Hook Infrastructure

1. **Create hook base structure**:
   ```
   agent_mcp/hooks/
   ├── file-lock-manager.js
   ├── activity-broadcaster.js
   ├── lock-utils.js
   └── config.json
   ```

2. **Implement file-lock-manager.js**:
   - Parse Claude Code hook input
   - Check for existing locks
   - Create/validate lock files
   - Return appropriate hook responses

3. **Implement activity-broadcaster.js**:
   - Log completed operations
   - Update activity feeds
   - Release locks
   - Broadcast status updates

### Phase 2: Integration with Agent System

1. **Update admin_tools.py**:
   - Remove branch isolation logic
   - Keep sandbox worktree creation on main branch
   - Register hooks automatically for all agents
   - Simplify termination process

2. **Hook Registration**:
   - Automatic hook setup during agent creation
   - Per-agent hook configuration
   - Integration with existing tmux session management

### Phase 3: Lock Management Infrastructure

1. **Create lock directories**:
   ```bash
   mkdir -p .agent-locks .agent-activity
   ```

2. **Implement lock utilities**:
   - Lock creation/deletion
   - Timeout monitoring
   - Cleanup processes
   - Admin override commands

3. **Activity tracking**:
   - Live feed generation
   - Agent status monitoring
   - Historical lock analysis

### Phase 4: Real-Time Dashboard

1. **Live activity feed**:
   - JSON Lines format for easy parsing
   - Real-time file operation logging
   - Agent status tracking

2. **Admin visibility tools**:
   - Current lock status display
   - Agent activity monitoring
   - Lock history and analytics

## Security and Safety Considerations

### File Access Control
- Locks only prevent concurrent editing, not reading
- No elevation of privileges beyond user permissions
- Lock files stored in project directory (not system-wide)

### Lock Safety Mechanisms
- Automatic timeout prevents indefinite locks
- Process monitoring detects agent crashes
- Admin override for emergency lock release
- Audit trail for all lock operations

### Hook Security
- Hooks execute with same permissions as Claude Code
- Input validation on all hook parameters
- No external network requests in critical hooks
- Fail-safe behavior (allow operation if lock check fails)

## Error Handling and Edge Cases

### Agent Crash During Lock
- Lock timeout mechanism (10 minutes default)
- Process monitoring detects crashed agents
- Automatic lock cleanup on agent termination
- Lock ownership verification before release

### Simultaneous Lock Requests
- Atomic lock file creation (filesystem-level)
- First-come-first-served basis
- Proper error messages for blocked agents
- Queue system for popular files (future enhancement)

### Network/Filesystem Issues
- Graceful degradation if lock directory unavailable
- Fallback to allow operations with warnings
- Lock consistency checking and repair
- Redundant lock verification

## Performance Considerations

### Lock Check Performance
- Simple file existence checks (fast)
- Lock directory caching
- Minimal overhead per operation
- Async activity broadcasting

### Scalability
- Supports dozens of concurrent agents
- Linear performance scaling
- Efficient lock cleanup
- Configurable timeout values

## Migration from Current System

### Step 1: Maintain Compatibility
- Keep existing worktree creation
- Add hooks alongside current system
- Test with limited agents initially

### Step 2: Gradual Transition
- Enable file locking for new agents
- Monitor performance and stability
- Resolve any integration issues

### Step 3: Full Migration
- Remove branch isolation logic
- Switch all agents to main branch
- Enable hooks for all operations
- Complete testing and validation

## Configuration Options

### Hook Configuration
```json
{
  "fileLocking": {
    "enabled": true,
    "lockTimeout": 600,
    "lockDirectory": ".agent-locks",
    "activityDirectory": ".agent-activity",
    "allowAdminOverride": true,
    "debugLogging": false
  }
}
```

### Per-Agent Settings
```json
{
  "agent_worker1": {
    "lockTimeout": 300,
    "priority": "high",
    "allowedOperations": ["Read", "Write", "Edit"]
  }
}
```

## Testing Strategy

### Unit Tests
- Lock manager functionality
- Activity broadcaster logic
- Lock timeout handling
- Error scenarios

### Integration Tests
- Multi-agent file conflicts
- Lock acquisition and release
- Agent termination cleanup
- Hook registration and execution

### Performance Tests
- Concurrent agent operations
- Lock check latency
- Activity feed performance
- System resource usage

### Scenario Tests
- Agent crash during lock
- Network interruption
- Filesystem permission issues
- High-concurrency scenarios

## Success Metrics

### Conflict Prevention
- Zero merge conflicts with multiple agents
- 100% successful lock acquisition tracking
- No lost work due to concurrent edits

### Visibility
- Real-time activity feed accuracy
- Complete audit trail of file operations
- Agent status tracking reliability

### Performance
- Lock check latency < 10ms
- Hook execution overhead < 100ms
- System supports 20+ concurrent agents

### Reliability
- 99.9% lock operation success rate
- Automatic recovery from failures
- Zero data corruption incidents

## Future Enhancements

### Advanced Features
- Directory-level locking
- File watch integration
- Intelligent lock queuing
- Predictive conflict detection

### Dashboard Improvements
- Real-time web dashboard
- Agent performance analytics
- Lock usage statistics
- Conflict resolution suggestions

### Integration Options
- IDE plugin integration
- Slack/Teams notifications
- CI/CD pipeline hooks
- External monitoring systems

## Conclusion

This file-level locking system provides the perfect balance of:
- **Real-time visibility** for verification and oversight
- **Conflict prevention** through deterministic locking
- **Shared collaboration** via main branch development
- **Auditable sandboxes** for individual agent tracking
- **Zero overhead** through automated hook management

The implementation leverages Claude Code's robust hook system to create a transparent, reliable, and scalable multi-agent development environment that maintains the benefits of collaboration while preventing the problems of concurrent editing conflicts.