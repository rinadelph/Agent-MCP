#!/usr/bin/env python3
"""
Example: Database Migration in Action

This example demonstrates how the Agent MCP database migration system works.
"""

import os
import sys
import asyncio
import sqlite3
from pathlib import Path

# Add agent_mcp to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set up a test environment
TEST_DIR = Path("/tmp/agent_mcp_migration_example")
TEST_DIR.mkdir(exist_ok=True)
os.environ["MCP_PROJECT_DIR"] = str(TEST_DIR)

# Create test database
from agent_mcp.utils.project_utils import init_agent_directory
from agent_mcp.db.schema import init_database
from agent_mcp.db.connection import get_db_connection


async def create_legacy_database():
    """Create a legacy v1.0 database with sample tasks"""
    print("Creating legacy database...")
    
    # Initialize directory structure
    init_agent_directory(str(TEST_DIR))
    
    # Create database with old schema
    conn = sqlite3.connect(TEST_DIR / ".agent" / "mcp_state.db")
    cursor = conn.cursor()
    
    # Create basic tasks table (v1.0 schema)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            assigned_to TEXT,
            created_by TEXT NOT NULL,
            status TEXT NOT NULL,
            priority TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            parent_task TEXT,
            child_tasks TEXT,
            depends_on_tasks TEXT,
            notes TEXT
        )
    """)
    
    # Add sample tasks
    sample_tasks = [
        ("task_001", "Set up database schema", "completed"),
        ("task_002", "Implement user authentication", "completed"),
        ("task_003", "Create login page", "completed"),
        ("task_004", "Build quote calculator", "in_progress"),
        ("task_005", "Add pricing logic", "in_progress"),
        ("task_006", "Create dashboard UI", "pending"),
        ("task_007", "Implement API endpoints", "pending"),
        ("task_008", "Add unit tests", "pending"),
    ]
    
    for task_id, title, status in sample_tasks:
        cursor.execute("""
            INSERT INTO tasks (
                task_id, title, description, assigned_to, created_by,
                status, priority, created_at, updated_at,
                parent_task, child_tasks, depends_on_tasks, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), ?, ?, ?, ?)
        """, (
            task_id, title, f"Description for {title}", None, "example_user",
            status, "medium", None, "[]", "[]", "[]"
        ))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Created legacy database with {len(sample_tasks)} tasks")


async def show_database_state(title: str):
    """Display current database state"""
    print(f"\n{'='*60}")
    print(title)
    print("="*60)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check for phases
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE task_id LIKE 'phase_%'")
    phase_count = cursor.fetchone()[0]
    
    # Check for workstreams
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE task_id LIKE 'root_%'")
    workstream_count = cursor.fetchone()[0]
    
    # Get total tasks
    cursor.execute("SELECT COUNT(*) FROM tasks")
    total_tasks = cursor.fetchone()[0]
    
    print(f"Total Tasks: {total_tasks}")
    print(f"Phases: {phase_count}")
    print(f"Workstreams: {workstream_count}")
    
    if phase_count > 0:
        print("\nPhase Structure:")
        cursor.execute("""
            SELECT p.title as phase, COUNT(w.task_id) as workstreams
            FROM tasks p
            LEFT JOIN tasks w ON w.parent_task = p.task_id
            WHERE p.task_id LIKE 'phase_%'
            GROUP BY p.task_id
            ORDER BY p.task_id
        """)
        
        for phase, ws_count in cursor.fetchall():
            print(f"  • {phase}: {ws_count} workstreams")
    else:
        print("\nTask List:")
        cursor.execute("SELECT task_id, title, status FROM tasks LIMIT 5")
        for task_id, title, status in cursor.fetchall():
            print(f"  • [{status}] {title}")
        
        remaining = total_tasks - 5
        if remaining > 0:
            print(f"  ... and {remaining} more tasks")
    
    conn.close()


async def run_migration_example():
    """Run the migration example"""
    print("\n🚀 Agent MCP Migration Example")
    print("This demonstrates automatic database migration from v1.0 to v2.0")
    
    # Step 1: Create legacy database
    await create_legacy_database()
    
    # Step 2: Show current state
    await show_database_state("BEFORE MIGRATION (Legacy v1.0)")
    
    # Step 3: Configure migration
    print("\n📋 Configuring migration...")
    os.environ["AGENT_MCP_MIGRATION_INTERACTIVE"] = "false"  # Non-interactive for demo
    os.environ["AGENT_MCP_MIGRATION_AUTO_BACKUP"] = "true"
    
    # Step 4: Run migration
    print("\n🔧 Running migration...")
    from agent_mcp.db.migrations.migration_manager import ensure_database_current
    
    success = await ensure_database_current()
    
    if success:
        print("\n✅ Migration completed successfully!")
        
        # Step 5: Show new state
        await show_database_state("AFTER MIGRATION (v2.0)")
        
        # Show backup created
        backup_files = list((TEST_DIR / ".agent").glob("*backup*.db"))
        if backup_files:
            print(f"\n💾 Backup created: {backup_files[0].name}")
    else:
        print("\n❌ Migration failed!")
    
    print("\n📁 Test files created in:", TEST_DIR)
    print("   Feel free to explore the migrated database!")


async def main():
    """Main entry point"""
    try:
        await run_migration_example()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())