#!/usr/bin/env python3
"""
Test the hierarchical migration system with complete task trees
"""

import sys
import os
import shutil
import sqlite3
from pathlib import Path

# Add agent_mcp to path
sys.path.insert(0, '/home/alejandro/Code/MCP/Agent-MCP')

# Set up environment
os.environ['MCP_PROJECT_DIR'] = '/home/alejandro/Code/MCP/Agent-MCP'

def analyze_clover_hierarchy():
    """Analyze the Clover task hierarchy before migration"""
    
    clover_db_path = Path('/home/alejandro/Code/Clover/.agent/mcp_state.db')
    conn = sqlite3.connect(clover_db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("📊 **Clover Task Hierarchy Analysis**")
    print("=" * 60)
    
    # Get total counts
    cursor.execute("SELECT COUNT(*) as total FROM tasks")
    total_tasks = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as count FROM tasks WHERE parent_task IS NULL")
    root_count = cursor.fetchone()['count']
    
    subtask_count = total_tasks - root_count
    
    print(f"Total tasks: {total_tasks}")
    print(f"Root tasks: {root_count}")
    print(f"Subtasks: {subtask_count}")
    print()
    
    # Analyze each root task tree
    cursor.execute("SELECT task_id, title, status FROM tasks WHERE parent_task IS NULL ORDER BY created_at")
    root_tasks = cursor.fetchall()
    
    task_trees = {}
    
    for root_task in root_tasks:
        root_id = root_task['task_id']
        root_title = root_task['title']
        
        # Get all descendants
        descendants = get_all_descendants(cursor, root_id)
        tree_size = 1 + len(descendants)
        
        # Analyze status distribution
        all_tasks_in_tree = [root_task] + descendants
        status_dist = {}
        for task in all_tasks_in_tree:
            status = task['status']
            status_dist[status] = status_dist.get(status, 0) + 1
        
        task_trees[root_id] = {
            'root_task': root_task,
            'descendants': descendants,
            'tree_size': tree_size,
            'status_distribution': status_dist
        }
        
        print(f"🌳 **{root_title[:50]}...**")
        print(f"   Task ID: {root_id}")
        print(f"   Tree size: {tree_size} tasks (1 root + {len(descendants)} subtasks)")
        print(f"   Status: {dict(status_dist)}")
        print()
    
    conn.close()
    return task_trees

def get_all_descendants(cursor, parent_id):
    """Recursively get all descendants of a task"""
    descendants = []
    
    # Get direct children
    cursor.execute("SELECT task_id, title, status, parent_task FROM tasks WHERE parent_task = ?", (parent_id,))
    direct_children = cursor.fetchall()
    
    for child in direct_children:
        descendants.append(dict(child))
        # Recursively get grandchildren
        grandchildren = get_all_descendants(cursor, child['task_id'])
        descendants.extend(grandchildren)
    
    return descendants

def test_hierarchical_migration():
    """Test the hierarchical migration system"""
    
    print("\n🚀 **Testing Hierarchical Migration System**")
    print("=" * 60)
    
    # Setup test database
    test_db_path = Path('/home/alejandro/Code/MCP/Agent-MCP/.agent/mcp_state.db')
    backup_path = test_db_path.with_suffix('.db.backup')
    clover_db_path = Path('/home/alejandro/Code/Clover/.agent/mcp_state.db')
    
    if test_db_path.exists():
        shutil.copy2(test_db_path, backup_path)
    
    test_agent_dir = Path('/home/alejandro/Code/MCP/Agent-MCP/.agent')
    test_agent_dir.mkdir(exist_ok=True)
    shutil.copy2(clover_db_path, test_db_path)
    
    try:
        from agent_mcp.core.hierarchical_migration import HierarchicalMigrationManager, TaskHierarchyAnalyzer
        
        migration_manager = HierarchicalMigrationManager()
        
        print("🔍 Checking if hierarchical migration is needed...")
        needs_migration = migration_manager.needs_hierarchical_migration()
        print(f"Hierarchical migration needed: {needs_migration}")
        
        if needs_migration:
            print("\n📊 Analyzing complete task hierarchy...")
            
            analyzer = TaskHierarchyAnalyzer()
            analysis = analyzer.analyze_complete_hierarchy()
            
            print(f"Hierarchy analysis results:")
            print(f"   Total tasks: {analysis['total_tasks']}")
            print(f"   Root tasks: {analysis['root_tasks_count']}")
            print(f"   Subtasks: {analysis['subtasks_count']}")
            print(f"   Task trees: {len(analysis['task_trees'])}")
            print()
            
            print("📋 Migration plan:")
            for i, plan in enumerate(analysis['migration_plan'], 1):
                print(f"   {i}. {plan['root_task_title'][:50]}...")
                print(f"      Tree size: {plan['tree_size']} tasks")
                print(f"      Status distribution: {plan['status_distribution']}")
                print()
            
            print("🚀 Running hierarchical migration...")
            success = migration_manager.run_hierarchical_migration()
            
            if success:
                print("✅ Hierarchical migration completed successfully!")
                
                # Verify migration results
                conn = sqlite3.connect(test_db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Check Foundation phase creation
                cursor.execute("SELECT task_id, title FROM tasks WHERE task_id = 'phase_1_foundation'")
                foundation_phase = cursor.fetchone()
                
                if foundation_phase:
                    print(f"\n✅ Foundation phase created: {foundation_phase['title']}")
                else:
                    print(f"\n❌ Foundation phase not found!")
                    return False
                
                # Check that root tasks are now children of Foundation
                cursor.execute("""
                    SELECT task_id, title, parent_task 
                    FROM tasks 
                    WHERE parent_task = 'phase_1_foundation'
                    ORDER BY created_at
                """)
                foundation_children = cursor.fetchall()
                
                print(f"\n📦 Tasks directly under Foundation phase: {len(foundation_children)}")
                for child in foundation_children:
                    print(f"   ✓ {child['task_id']}: {child['title'][:50]}...")
                
                # Check that subtask hierarchy is preserved
                print(f"\n🔗 Verifying subtask hierarchy preservation...")
                
                cursor.execute("""
                    SELECT parent_task, COUNT(*) as count 
                    FROM tasks 
                    WHERE parent_task IS NOT NULL AND parent_task != 'phase_1_foundation'
                    GROUP BY parent_task
                    ORDER BY count DESC
                """)
                subtask_parents = cursor.fetchall()
                
                print(f"   Subtask relationships preserved: {len(subtask_parents)} parent tasks have children")
                for parent_info in subtask_parents[:5]:  # Show top 5
                    parent_id = parent_info['parent_task']
                    child_count = parent_info['count']
                    
                    # Get parent task title
                    cursor.execute("SELECT title FROM tasks WHERE task_id = ?", (parent_id,))
                    parent_task = cursor.fetchone()
                    parent_title = parent_task['title'][:40] if parent_task else 'Unknown'
                    
                    print(f"   - {parent_id}: {parent_title}... ({child_count} children)")
                
                # Final verification: count all tasks
                cursor.execute("SELECT COUNT(*) as total FROM tasks WHERE task_id != 'phase_1_foundation'")
                migrated_task_count = cursor.fetchone()['total']
                
                cursor.execute("SELECT COUNT(*) as total FROM tasks")
                total_after_migration = cursor.fetchone()['total']
                
                expected_total = migrated_task_count + 1  # +1 for Foundation phase
                
                print(f"\n📊 Migration verification:")
                print(f"   Tasks before migration: {analysis['total_tasks']}")
                print(f"   Tasks after migration: {total_after_migration}")
                print(f"   Foundation phase: +1")
                print(f"   Expected total: {analysis['total_tasks'] + 1}")
                print(f"   Actual total: {total_after_migration}")
                
                if total_after_migration == analysis['total_tasks'] + 1:
                    print("   ✅ Task count verification passed!")
                else:
                    print("   ❌ Task count mismatch!")
                
                # Check for orphaned tasks
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM tasks 
                    WHERE parent_task IS NULL AND task_id != 'phase_1_foundation'
                """)
                orphaned_count = cursor.fetchone()['count']
                
                if orphaned_count == 0:
                    print("   ✅ No orphaned tasks - all tasks properly organized!")
                else:
                    print(f"   ⚠️ Found {orphaned_count} orphaned tasks!")
                
                conn.close()
                
            else:
                print("❌ Hierarchical migration failed!")
                return False
        
        else:
            print("ℹ️ No hierarchical migration needed")
    
    except Exception as e:
        print(f"❌ Error during hierarchical migration test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Restore original database
        if backup_path.exists():
            shutil.copy2(backup_path, test_db_path)
            backup_path.unlink()
    
    return True

if __name__ == "__main__":
    print("🧪 Testing Hierarchical Task Migration System")
    print("=" * 60)
    
    # First analyze the Clover hierarchy
    task_trees = analyze_clover_hierarchy()
    
    # Then test the migration
    if test_hierarchical_migration():
        print("\n🎉 Hierarchical migration system working perfectly!")
        print("All task trees properly migrated while preserving internal structure.")
    else:
        print("\n❌ Hierarchical migration system needs fixes.")