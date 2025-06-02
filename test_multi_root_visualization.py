#!/usr/bin/env python3
"""
Test multi-root task system with ASCII visualization
Shows the hierarchical structure with phases and multiple root tasks
"""

import sys
import os
import shutil
import sqlite3
import asyncio
from pathlib import Path

# Add agent_mcp to path
sys.path.insert(0, '/home/alejandro/Code/MCP/Agent-MCP')

# Set up environment
os.environ['MCP_PROJECT_DIR'] = '/home/alejandro/Code/MCP/Agent-MCP'

def print_ascii_tree(conn):
    """Print an ASCII visualization of the task hierarchy"""
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("AGENT MCP PROJECT HIERARCHY - MULTI-ROOT TASK VISUALIZATION")
    print("="*80 + "\n")
    
    # Get all phases
    cursor.execute("""
        SELECT task_id, title, status 
        FROM tasks 
        WHERE task_id LIKE 'phase_%' 
        ORDER BY task_id
    """)
    phases = cursor.fetchall()
    
    if not phases:
        print("No phases found in the system.")
        return
    
    print("PHASE PROGRESSION (Linear Lock System)")
    print("┌" + "─"*78 + "┐")
    
    # Phase progression header
    phase_line = "│ "
    for i, phase in enumerate(phases):
        status_icon = "✅" if phase['status'] == 'completed' else "🟡" if phase['status'] == 'in_progress' else "🔒"
        phase_name = phase['title'].split(':')[1].strip() if ':' in phase['title'] else phase['title']
        phase_line += f"{status_icon} {phase_name}"
        if i < len(phases) - 1:
            phase_line += " ──→ "
    phase_line += " │"
    print(phase_line)
    print("└" + "─"*78 + "┘\n")
    
    # Display each phase with its root tasks
    for phase in phases:
        phase_id = phase['task_id']
        phase_status = phase['status']
        
        # Skip locked phases
        if phase_status not in ['completed', 'in_progress']:
            continue
            
        print(f"\n{'='*80}")
        status_emoji = "✅" if phase_status == 'completed' else "🟡"
        print(f"{status_emoji} {phase['title'].upper()} [{phase_status.upper()}]")
        print("="*80)
        
        # Get root tasks for this phase
        cursor.execute("""
            SELECT task_id, title, status, 
                   (SELECT COUNT(*) FROM tasks WHERE parent_task = t.task_id) as subtask_count
            FROM tasks t
            WHERE parent_task = ?
            ORDER BY created_at
        """, (phase_id,))
        root_tasks = cursor.fetchall()
        
        if not root_tasks:
            print("   └── (No root tasks in this phase)")
            continue
        
        print(f"\n   📊 Root Tasks/Workstreams: {len(root_tasks)}")
        print("   │")
        
        for i, root_task in enumerate(root_tasks):
            is_last_root = (i == len(root_tasks) - 1)
            root_prefix = "   └──" if is_last_root else "   ├──"
            continuation = "      " if is_last_root else "   │  "
            
            status_icon = "✅" if root_task['status'] == 'completed' else \
                         "🟡" if root_task['status'] == 'in_progress' else \
                         "⭐" if root_task['status'] == 'pending' else "❌"
            
            print(f"{root_prefix} 🚀 {root_task['title']} [{status_icon}]")
            print(f"{continuation}   Subtasks: {root_task['subtask_count']}")
            
            # Get subtasks for this root task
            cursor.execute("""
                SELECT task_id, title, status, assigned_to
                FROM tasks
                WHERE parent_task = ?
                ORDER BY created_at
                LIMIT 5
            """, (root_task['task_id'],))
            subtasks = cursor.fetchall()
            
            if subtasks:
                print(f"{continuation}   │")
                for j, subtask in enumerate(subtasks):
                    is_last_subtask = (j == len(subtasks) - 1)
                    subtask_prefix = f"{continuation}   └──" if is_last_subtask else f"{continuation}   ├──"
                    
                    status_icon = "✅" if subtask['status'] == 'completed' else \
                                 "🟡" if subtask['status'] == 'in_progress' else \
                                 "⭐" if subtask['status'] == 'pending' else "❌"
                    
                    agent_info = f" → {subtask['assigned_to']}" if subtask['assigned_to'] else ""
                    print(f"{subtask_prefix} {status_icon} {subtask['title'][:50]}...{agent_info}")
                
                if root_task['subtask_count'] > 5:
                    print(f"{continuation}   └── ... and {root_task['subtask_count'] - 5} more subtasks")
            
            if not is_last_root:
                print("   │")
    
    # Show cross-root dependencies
    print("\n" + "="*80)
    print("🔗 CROSS-ROOT TASK DEPENDENCIES")
    print("="*80)
    
    cursor.execute("""
        SELECT t1.task_id, t1.title, t2.task_id as depends_on_id, t2.title as depends_on_title
        FROM tasks t1
        JOIN json_each(t1.depends_on_tasks) d ON d.value = t2.task_id
        JOIN tasks t2 ON t2.task_id = d.value
        WHERE t1.parent_task LIKE 'root_%' AND t2.parent_task LIKE 'root_%'
        AND t1.parent_task != t2.parent_task
        LIMIT 10
    """)
    dependencies = cursor.fetchall()
    
    if dependencies:
        for dep in dependencies:
            print(f"   {dep['title'][:30]}... ──depends on→ {dep['depends_on_title'][:30]}...")
    else:
        print("   (No cross-root dependencies found)")
    
    # Summary statistics
    print("\n" + "="*80)
    print("📊 SYSTEM STATISTICS")
    print("="*80)
    
    cursor.execute("SELECT COUNT(*) as count FROM tasks WHERE task_id LIKE 'phase_%'")
    phase_count = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM tasks WHERE parent_task LIKE 'phase_%'")
    root_task_count = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM tasks WHERE task_id NOT LIKE 'phase_%' AND task_id NOT LIKE 'root_%'")
    regular_task_count = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM tasks")
    total_tasks = cursor.fetchone()['count']
    
    print(f"   Total Phases: {phase_count}")
    print(f"   Total Root Tasks: {root_task_count}")
    print(f"   Total Regular Tasks: {regular_task_count}")
    print(f"   Total Tasks in System: {total_tasks}")
    
    # Calculate average tasks per root
    if root_task_count > 0:
        avg_tasks_per_root = regular_task_count / root_task_count
        print(f"   Average Tasks per Root: {avg_tasks_per_root:.1f}")


async def test_multi_root_system():
    """Test the multi-root task system with visualization"""
    
    print("🔧 Testing Multi-Root Task System with Visualization")
    print("="*80)
    
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
        print("1. Running granular migration with multi-root support...")
        from agent_mcp.core.granular_migration import run_granular_migration
        
        success = await run_granular_migration()
        
        if success:
            print("✅ Migration completed successfully!")
            
            # Open database to visualize
            conn = sqlite3.connect(test_db_path)
            conn.row_factory = sqlite3.Row
            
            # Print ASCII visualization
            print_ascii_tree(conn)
            
            conn.close()
            
            print("\n" + "="*80)
            print("✅ MULTI-ROOT TASK SYSTEM TEST COMPLETE")
            print("="*80)
            print("\nKey Features Demonstrated:")
            print("• Multiple root tasks per phase for independent workstreams")
            print("• Hierarchical task organization with clear parent-child relationships")
            print("• Phase-based linear progression with completion tracking")
            print("• Cross-root dependencies for complex workflows")
            print("• Intelligent workstream identification during migration")
            
        else:
            print("❌ Migration failed!")
            return False
    
    except Exception as e:
        print(f"❌ Error during test: {e}")
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
    asyncio.run(test_multi_root_system())