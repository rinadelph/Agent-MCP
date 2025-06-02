# 📚 Agent MCP Database Migration System

## Overview

Agent MCP includes an automatic database migration system that ensures your database schema is always up-to-date with the latest version. When you run Agent MCP, it automatically detects your database version and applies any necessary migrations.

## How It Works

### Automatic Migration on Startup

1. **Version Detection**: When Agent MCP starts, it checks your database version
2. **Migration Check**: If your database is outdated, it identifies needed migrations
3. **User Confirmation**: In interactive mode, it asks for confirmation
4. **Backup Creation**: Automatically creates a backup before migrating
5. **Migration Execution**: Applies migrations in sequence
6. **Version Recording**: Records successful migrations in the database

### Version History

| Version | Description | Key Changes |
|---------|-------------|-------------|
| 1.0.0 | Initial schema | Flat task structure |
| 1.1.0 | Code support | Added code_language, code_content fields |
| 2.0.0 | Multi-root architecture | Phases, workstreams, hierarchy preservation |

## Configuration

### Environment Variables

Configure migration behavior using environment variables:

```bash
# Disable automatic migration
export AGENT_MCP_MIGRATION_AUTO_MIGRATE=false

# Disable interactive prompts
export AGENT_MCP_MIGRATION_INTERACTIVE=false

# Disable automatic backups
export AGENT_MCP_MIGRATION_AUTO_BACKUP=false

# Set backup retention (days)
export AGENT_MCP_MIGRATION_BACKUP_RETENTION_DAYS=30

# Workstream configuration
export AGENT_MCP_MIGRATION_MIN_TASKS_PER_WORKSTREAM=5
export AGENT_MCP_MIGRATION_MAX_WORKSTREAMS_PER_PHASE=7
```

### Configuration File

Create `.agent/migration.conf` in your project directory:

```ini
# Agent MCP Migration Configuration
auto_migrate = true
interactive = true
auto_backup = true
backup_retention_days = 7
preserve_hierarchies = true
consolidate_workstreams = true
min_tasks_per_workstream = 5
max_workstreams_per_phase = 7
```

## CLI Commands

### Check Database Version

```bash
agent-mcp migrate --check
```

Output:
```
============================
DATABASE VERSION INFORMATION
============================
Current Schema Version: 2.0.0

Migration History:
  • 2.0.0: Multi-root task architecture with phases and workstreams
    Applied: 2024-01-06T10:30:00
  • 1.1.0: Added code support fields
    Applied: 2024-01-05T14:20:00
```

### Run Migration Manually

```bash
# Interactive migration (default)
agent-mcp migrate

# Force migration without prompts
agent-mcp migrate --force

# Skip backup creation
agent-mcp migrate --no-backup
```

### Configure Migration

```bash
# Show current configuration
agent-mcp migrate --config

# Set configuration values
agent-mcp migrate --set auto_migrate=false
agent-mcp migrate --set min_tasks_per_workstream=3
```

## Migration Details

### Version 2.0.0: Multi-Root Task Architecture

This major migration transforms your flat task structure into a hierarchical, phase-based system:

#### What It Does:

1. **Creates Phases**: Organizes tasks into 4 phases:
   - Foundation (infrastructure, setup)
   - Intelligence (core features, business logic)
   - Coordination (UI, integration)
   - Optimization (performance, testing)

2. **Creates Workstreams**: Groups related tasks into logical workstreams:
   - Analyzes task relationships and dependencies
   - Creates natural task clusters
   - Preserves parent-child hierarchies
   - Ensures no orphaned tasks

3. **Preserves Relationships**:
   - Maintains existing task hierarchies
   - Keeps dependencies within workstreams
   - Respects task completion status

#### Example Transformation:

**Before Migration:**
```
- 147 flat tasks
- No clear organization
- Mixed dependencies
```

**After Migration:**
```
Phase 1: Foundation
  └─ Authentication & User Management (13 tasks)
  └─ Database Architecture (9 tasks)
  └─ API Development (5 tasks)

Phase 2: Intelligence  
  └─ Dashboard Features (17 tasks)
  └─ Quote Calculator System (8 tasks)
```

## Backup Management

### Automatic Backups

- Created before each migration
- Named: `mcp_state_backup_YYYYMMDD_HHMMSS.db`
- Stored in `.agent/` directory
- Automatically cleaned up after retention period

### Manual Backup Restore

If a migration fails:

```bash
# Find your backup
ls .agent/*backup*.db

# Restore manually
cp .agent/mcp_state_backup_20240106_103000.db .agent/mcp_state.db
```

## Troubleshooting

### Migration Fails

1. **Check logs** for specific error messages
2. **Restore from backup** (automatically created)
3. **Disable auto-migration** and investigate:
   ```bash
   export AGENT_MCP_MIGRATION_AUTO_MIGRATE=false
   ```

### Database Locked

If you see "database is locked" errors:
1. Ensure no other Agent MCP instances are running
2. Check for zombie processes
3. Restart and try again

### Custom Database Location

If using a custom database location:
```bash
export MCP_PROJECT_DIR=/path/to/your/project
agent-mcp migrate
```

## Best Practices

1. **Always backup** before major operations
2. **Test migrations** on a copy first
3. **Review changes** after migration
4. **Keep backups** for at least 7 days
5. **Monitor logs** during migration

## FAQ

### Q: Can I disable automatic migration?
A: Yes, set `AGENT_MCP_MIGRATION_AUTO_MIGRATE=false`

### Q: How do I know if my database needs migration?
A: Run `agent-mcp migrate --check` to see current version

### Q: What happens to my existing tasks?
A: All tasks are preserved and intelligently organized into phases and workstreams

### Q: Can I customize workstream organization?
A: Yes, use configuration options like `min_tasks_per_workstream`

### Q: Is migration reversible?
A: No, but backups are created automatically. Always test on a copy first.

### Q: What if I have custom schema modifications?
A: Migration preserves unknown columns and tables. Test thoroughly.

## Technical Details

### Migration Process

1. **Relationship Analysis**: Analyzes parent-child and dependency relationships
2. **Cluster Detection**: Identifies natural task groupings
3. **Phase Assignment**: Assigns clusters to appropriate phases based on status
4. **Workstream Creation**: Creates workstream root tasks for each cluster
5. **Hierarchy Preservation**: Maintains task relationships within workstreams
6. **Validation**: Ensures no tasks are orphaned

### Database Schema Changes

Version 2.0.0 adds:
- Phase tasks (task_id: `phase_*`)
- Workstream root tasks (task_id: `root_*`)
- Migration tracking table (`schema_migrations`)

No columns are removed, ensuring backward compatibility.