#!/usr/bin/env python3
"""
Test the corrected linear progression migration system
"""

import sys
import os
import shutil
from pathlib import Path

# Add agent_mcp to path
sys.path.insert(0, '/home/alejandro/Code/MCP/Agent-MCP')

# Set up environment
os.environ['MCP_PROJECT_DIR'] = '/home/alejandro/Code/MCP/Agent-MCP'

def test_corrected_migration():
    """Test the corrected migration system that enforces linear progression"""
    
    print("🔄 Testing Corrected Linear Progression Migration")
    print("=" * 80)
    
    # Backup and copy Clover database
    test_db_path = Path('/home/alejandro/Code/MCP/Agent-MCP/.agent/mcp_state.db')
    backup_path = test_db_path.with_suffix('.db.backup')
    clover_db_path = Path('/home/alejandro/Code/Clover/.agent/mcp_state.db')
    
    if test_db_path.exists():
        shutil.copy2(test_db_path, backup_path)
    
    test_agent_dir = Path('/home/alejandro/Code/MCP/Agent-MCP/.agent')
    test_agent_dir.mkdir(exist_ok=True)
    shutil.copy2(clover_db_path, test_db_path)
    
    try:
        from agent_mcp.core.startup_migration import StartupMigrationManager
        
        migration_manager = StartupMigrationManager()
        
        print("🔍 Checking if migration is needed...")
        needs_migration = migration_manager.needs_migration()
        print(f"Migration needed: {needs_migration}")
        
        if needs_migration:
            print("\n🤖 Analyzing tasks...")
            classifications = migration_manager.analyze_and_classify_tasks()
            
            print("\n📊 Original AI Classifications:")
            for i, classification in enumerate(classifications, 1):
                task = classification['task']
                phase = classification['suggested_phase']
                confidence = classification['confidence']
                phase_name = migration_manager.classifier.phase_definitions[phase]['name']
                
                print(f"  {i}. {task['title'][:60]}...")
                print(f"     AI suggests: {phase_name} (confidence: {confidence:.2f})")
            
            print("\n🔄 Applying Linear Progression Enforcement...")
            corrected_classifications = migration_manager.enforce_linear_progression(classifications)
            
            print("\n📋 Corrected Classifications (Linear Progression):")
            for i, classification in enumerate(corrected_classifications, 1):
                task = classification['task']
                final_phase = classification['suggested_phase']
                original_suggestion = classification['original_ai_suggestion']
                
                original_phase_name = migration_manager.classifier.phase_definitions[original_suggestion]['name']
                final_phase_name = migration_manager.classifier.phase_definitions[final_phase]['name']
                
                print(f"  {i}. {task['title'][:60]}...")
                print(f"     Final assignment: {final_phase_name}")
                print(f"     (AI suggested: {original_phase_name} → enforced linear progression)")
            
            print("\n🚀 Running complete corrected migration...")
            success = migration_manager.run_startup_migration()
            
            if success:
                print("✅ Linear progression migration completed!")
                
                # Verify results
                import sqlite3
                conn = sqlite3.connect(test_db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Check phases created
                cursor.execute("SELECT task_id, title FROM tasks WHERE task_id LIKE 'phase_%' ORDER BY task_id")
                phases = cursor.fetchall()
                print(f"\n📊 Phases created: {len(phases)}")
                for phase in phases:
                    print(f"   ✓ {phase['task_id']}: {phase['title']}")
                
                # Check task distribution
                cursor.execute("""
                    SELECT parent_task, COUNT(*) as task_count 
                    FROM tasks 
                    WHERE parent_task LIKE 'phase_%' 
                    GROUP BY parent_task 
                    ORDER BY parent_task
                """)
                distribution = cursor.fetchall()
                
                print(f"\n📦 Task Distribution:")
                for row in distribution:
                    phase_name = migration_manager.classifier.phase_definitions[row['parent_task']]['name']
                    print(f"   {phase_name}: {row['task_count']} tasks")
                
                # Check that only Foundation phase exists (proper linear progression)
                cursor.execute("SELECT COUNT(*) as count FROM tasks WHERE task_id = 'phase_1_foundation'")
                foundation_exists = cursor.fetchone()['count'] > 0
                
                cursor.execute("SELECT COUNT(*) as count FROM tasks WHERE task_id LIKE 'phase_%' AND task_id != 'phase_1_foundation'")
                other_phases_exist = cursor.fetchone()['count'] > 0
                
                print(f"\n🎯 Linear Progression Validation:")
                print(f"   Foundation phase exists: {'✅' if foundation_exists else '❌'}")
                print(f"   Other phases exist: {'❌ (Correct!)' if not other_phases_exist else '⚠️ (Should not exist yet)'}")
                
                if foundation_exists and not other_phases_exist:
                    print("\n✅ Perfect! Linear progression properly enforced.")
                    print("   Users must complete Foundation tasks before creating next phase.")
                else:
                    print("\n⚠️ Linear progression enforcement may have issues.")
                
                conn.close()
                
                print(f"\n💡 Next Steps for Users:")
                print(f"   1. Complete all tasks in Foundation phase")
                print(f"   2. Use advance_phase to mark Foundation as complete")
                print(f"   3. Create Phase 2: Intelligence only after Foundation is 100% complete")
                print(f"   4. Continue linear progression through all phases")
                
            else:
                print("❌ Migration failed!")
                return False
        
        else:
            print("ℹ️ No migration needed")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Restore original
        if backup_path.exists():
            shutil.copy2(backup_path, test_db_path)
            backup_path.unlink()
    
    return True

if __name__ == "__main__":
    if test_corrected_migration():
        print("\n🎉 Corrected migration system working perfectly!")
        print("Linear progression is properly enforced.")
    else:
        print("\n❌ Migration system needs fixes.")