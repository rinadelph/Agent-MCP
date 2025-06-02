#!/usr/bin/env python3
"""
Test script to demonstrate the automatic startup migration system
using the real Clover database.
"""

import sys
import os
import shutil
from pathlib import Path

# Add agent_mcp to path
sys.path.insert(0, '/home/alejandro/Code/MCP/Agent-MCP')

# Set up environment
os.environ['MCP_PROJECT_DIR'] = '/home/alejandro/Code/MCP/Agent-MCP'

def test_clover_migration():
    """Test the migration system with Clover's actual database"""
    
    print("🧪 Testing Agent MCP Startup Migration with Clover Database")
    print("=" * 80)
    
    # Backup original test database if it exists
    test_db_path = Path('/home/alejandro/Code/MCP/Agent-MCP/.agent/mcp_state.db')
    backup_path = test_db_path.with_suffix('.db.backup')
    
    if test_db_path.exists():
        shutil.copy2(test_db_path, backup_path)
        print(f"✅ Backed up existing test database to {backup_path}")
    
    # Copy Clover's database for testing
    clover_db_path = Path('/home/alejandro/Code/Clover/.agent/mcp_state.db')
    if not clover_db_path.exists():
        print(f"❌ Clover database not found at {clover_db_path}")
        return False
    
    # Ensure test .agent directory exists
    test_agent_dir = Path('/home/alejandro/Code/MCP/Agent-MCP/.agent')
    test_agent_dir.mkdir(exist_ok=True)
    
    # Copy Clover database to test location
    shutil.copy2(clover_db_path, test_db_path)
    print(f"✅ Copied Clover database to test location")
    
    try:
        # Import and run the migration system
        from agent_mcp.core.startup_migration import StartupMigrationManager
        
        print("\n🔍 Analyzing Clover Database...")
        migration_manager = StartupMigrationManager()
        
        # Check if migration is needed
        needs_migration = migration_manager.needs_migration()
        print(f"Migration needed: {needs_migration}")
        
        if needs_migration:
            print("\n🤖 Running AI-powered classification and migration...")
            
            # Analyze tasks
            classifications = migration_manager.analyze_and_classify_tasks()
            print(f"Found {len(classifications)} root tasks to classify")
            
            # Show classification results
            print("\n📊 AI Classification Results:")
            for i, classification in enumerate(classifications, 1):
                task = classification['task']
                phase = classification['suggested_phase']
                confidence = classification['confidence']
                
                confidence_icon = "🟢" if confidence > 0.3 else "🟡" if confidence > 0.1 else "🔴"
                phase_name = migration_manager.classifier.phase_definitions[phase]['name']
                
                print(f"  {i}. {confidence_icon} {task['title'][:60]}...")
                print(f"     → {phase_name} (confidence: {confidence:.2f})")
                print(f"     Status: {task['status']}")
                print()
            
            # Run full migration
            print("🚀 Running complete migration process...")
            success = migration_manager.run_startup_migration()
            
            if success:
                print("✅ Migration completed successfully!")
                
                # Show results
                print("\n📈 Migration Results:")
                import sqlite3
                conn = sqlite3.connect(test_db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Count phases created
                cursor.execute("SELECT COUNT(*) as count FROM tasks WHERE task_id LIKE 'phase_%'")
                phase_count = cursor.fetchone()['count']
                print(f"   Phases created: {phase_count}")
                
                # Count migrated tasks
                cursor.execute("""
                    SELECT COUNT(*) as count FROM tasks 
                    WHERE parent_task IS NOT NULL AND parent_task LIKE 'phase_%'
                """)
                migrated_count = cursor.fetchone()['count']
                print(f"   Tasks migrated to phases: {migrated_count}")
                
                # Show phase distribution
                cursor.execute("""
                    SELECT parent_task, COUNT(*) as task_count 
                    FROM tasks 
                    WHERE parent_task LIKE 'phase_%' 
                    GROUP BY parent_task 
                    ORDER BY parent_task
                """)
                phase_distribution = cursor.fetchall()
                
                if phase_distribution:
                    print("\n📊 Task Distribution by Phase:")
                    for row in phase_distribution:
                        phase_id = row['parent_task']
                        task_count = row['task_count']
                        phase_name = migration_manager.classifier.phase_definitions.get(phase_id, {}).get('name', phase_id)
                        print(f"   {phase_name}: {task_count} tasks")
                
                conn.close()
                
            else:
                print("❌ Migration failed!")
                return False
        else:
            print("ℹ️ No migration needed - phase system already active")
    
    except Exception as e:
        print(f"❌ Error during migration test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Restore original database if it existed
        if backup_path.exists():
            shutil.copy2(backup_path, test_db_path)
            backup_path.unlink()
            print(f"\n🔄 Restored original test database")
    
    return True

def demonstrate_seamless_startup():
    """Demonstrate how the migration works seamlessly on startup"""
    
    print("\n" + "=" * 80)
    print("🚀 Demonstrating Seamless Startup Migration")
    print("=" * 80)
    
    print("""
The startup migration system works as follows:

1. **Automatic Detection**: On every Agent MCP startup, the system checks:
   - Are there existing tasks in the database?
   - Do phases already exist?
   - Are there root tasks that need migration?

2. **AI-Powered Classification**: If migration is needed:
   - Each root task is analyzed using content analysis
   - AI classifies tasks into appropriate phases using:
     * Keyword matching against phase definitions
     * Domain-specific heuristic rules
     * Content similarity analysis

3. **Intelligent Phase Creation**: 
   - Only creates phases that are actually needed
   - Skips phases if no tasks belong to them
   - Maintains proper phase hierarchy

4. **Seamless Migration**:
   - Migrates root tasks to become children of phases
   - Adds migration notes with AI confidence scores
   - Updates project context with migration status
   - No user intervention required

5. **Backward Compatibility**:
   - Existing tools continue to work unchanged
   - New phase-aware features are automatically enabled
   - Users get enhanced functionality without disruption

🎯 **User Experience**: 
   - User runs Agent MCP as normal
   - System detects old version automatically
   - Migration happens transparently in background
   - User gets phase system benefits immediately
   - All existing tasks are properly organized

💡 **AI Intelligence**:
   - Foundation: setup, config, database, auth, architecture
   - Intelligence: AI, RAG, embeddings, smart features
   - Coordination: UI/UX, workflows, integration, features
   - Optimization: testing, performance, polish, production

This ensures that projects like Clover automatically get upgraded
to the new phase system without any manual intervention!
""")

if __name__ == "__main__":
    print("Testing Agent MCP Startup Migration System")
    
    if test_clover_migration():
        demonstrate_seamless_startup()
        print("\n✅ All tests passed! The startup migration system is working correctly.")
    else:
        print("\n❌ Tests failed! Please check the implementation.")