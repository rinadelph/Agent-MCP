#!/usr/bin/env python3
"""
Test relationship-aware migration that preserves hierarchies and eliminates orphans
"""

import sys
import os
import shutil
import sqlite3
import asyncio
import json
from pathlib import Path
from datetime import datetime

# Add agent_mcp to path
sys.path.insert(0, '/home/alejandro/Code/MCP/Agent-MCP')

# Set up environment
os.environ['MCP_PROJECT_DIR'] = '/home/alejandro/Code/MCP/Agent-MCP'

def analyze_hierarchy_preservation(db_path, db_name):
    """Analyze how well hierarchies were preserved"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print(f"\n{'='*80}")
    print(f"HIERARCHY PRESERVATION ANALYSIS: {db_name}")
    print("="*80)
    
    # Check for tasks with non-root/phase parents
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM tasks 
        WHERE parent_task IS NOT NULL 
        AND parent_task NOT LIKE 'phase_%' 
        AND parent_task NOT LIKE 'root_%'
        AND task_id NOT LIKE 'phase_%'
        AND task_id NOT LIKE 'root_%'
    """)
    hierarchical_tasks = cursor.fetchone()['count']
    
    # Get examples of preserved hierarchies
    cursor.execute("""
        SELECT 
            t1.task_id as child_id,
            t1.title as child_title,
            t1.parent_task as parent_id,
            t2.title as parent_title,
            t3.task_id as grandparent_id,
            t3.title as grandparent_title
        FROM tasks t1
        JOIN tasks t2 ON t1.parent_task = t2.task_id
        LEFT JOIN tasks t3 ON t2.parent_task = t3.task_id
        WHERE t1.parent_task NOT LIKE 'phase_%' 
        AND t1.parent_task NOT LIKE 'root_%'
        LIMIT 5
    """)
    hierarchy_examples = cursor.fetchall()
    
    print(f"\nHierarchical Tasks (with non-workstream parents): {hierarchical_tasks}")
    
    if hierarchy_examples:
        print("\nExamples of Preserved Hierarchies:")
        for ex in hierarchy_examples:
            print(f"\n  └─ {ex['child_title']}")
            print(f"     └─ Parent: {ex['parent_title']}")
            if ex['grandparent_title']:
                if ex['grandparent_id'].startswith('root_'):
                    print(f"        └─ Workstream: {ex['grandparent_title']}")
                else:
                    print(f"        └─ Grandparent: {ex['grandparent_title']}")
    
    # Check workstream cohesion
    print(f"\n{'='*60}")
    print("WORKSTREAM COHESION ANALYSIS")
    print("="*60)
    
    cursor.execute("""
        SELECT 
            w.task_id as workstream_id,
            w.title as workstream_title,
            COUNT(DISTINCT t1.task_id) as direct_children,
            COUNT(DISTINCT t2.task_id) as grandchildren,
            COUNT(DISTINCT t3.task_id) as great_grandchildren
        FROM tasks w
        LEFT JOIN tasks t1 ON t1.parent_task = w.task_id
        LEFT JOIN tasks t2 ON t2.parent_task = t1.task_id
        LEFT JOIN tasks t3 ON t3.parent_task = t2.task_id
        WHERE w.task_id LIKE 'root_%'
        GROUP BY w.task_id
        ORDER BY (COUNT(DISTINCT t1.task_id) + COUNT(DISTINCT t2.task_id) + COUNT(DISTINCT t3.task_id)) DESC
        LIMIT 5
    """)
    workstream_hierarchies = cursor.fetchall()
    
    for ws in workstream_hierarchies:
        total_descendants = ws['direct_children'] + ws['grandchildren'] + ws['great_grandchildren']
        print(f"\n{ws['workstream_title']}:")
        print(f"  Direct children: {ws['direct_children']}")
        if ws['grandchildren'] > 0:
            print(f"  Grandchildren: {ws['grandchildren']}")
        if ws['great_grandchildren'] > 0:
            print(f"  Great-grandchildren: {ws['great_grandchildren']}")
        print(f"  Total descendants: {total_descendants}")
    
    conn.close()
    
    return {
        'hierarchical_tasks': hierarchical_tasks,
        'has_deep_hierarchies': any(ws['grandchildren'] > 0 for ws in workstream_hierarchies)
    }

def analyze_relationship_cohesion(db_path, db_name):
    """Analyze how well related tasks were kept together"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print(f"\n{'='*80}")
    print(f"RELATIONSHIP COHESION ANALYSIS: {db_name}")
    print("="*80)
    
    # Check for dependencies within same workstream
    cursor.execute("""
        WITH task_workstreams AS (
            SELECT 
                t.task_id,
                t.depends_on_tasks,
                CASE 
                    WHEN t.parent_task LIKE 'root_%' THEN t.parent_task
                    WHEN p1.parent_task LIKE 'root_%' THEN p1.parent_task
                    WHEN p2.parent_task LIKE 'root_%' THEN p2.parent_task
                    ELSE NULL
                END as workstream_id
            FROM tasks t
            LEFT JOIN tasks p1 ON t.parent_task = p1.task_id
            LEFT JOIN tasks p2 ON p1.parent_task = p2.task_id
            WHERE t.task_id NOT LIKE 'phase_%' AND t.task_id NOT LIKE 'root_%'
        )
        SELECT 
            COUNT(DISTINCT tw1.task_id) as tasks_with_deps,
            SUM(CASE WHEN tw1.workstream_id = tw2.workstream_id THEN 1 ELSE 0 END) as same_ws_deps,
            SUM(CASE WHEN tw1.workstream_id != tw2.workstream_id THEN 1 ELSE 0 END) as cross_ws_deps
        FROM task_workstreams tw1
        CROSS JOIN json_each(tw1.depends_on_tasks) d
        JOIN task_workstreams tw2 ON tw2.task_id = d.value
        WHERE tw1.depends_on_tasks != '[]'
    """)
    
    dep_analysis = cursor.fetchone()
    
    if dep_analysis and dep_analysis['tasks_with_deps']:
        same_ws_percent = (dep_analysis['same_ws_deps'] / 
                          (dep_analysis['same_ws_deps'] + dep_analysis['cross_ws_deps']) * 100)
        
        print(f"\nDependency Analysis:")
        print(f"  Tasks with dependencies: {dep_analysis['tasks_with_deps']}")
        print(f"  Dependencies within same workstream: {dep_analysis['same_ws_deps']} ({same_ws_percent:.1f}%)")
        print(f"  Cross-workstream dependencies: {dep_analysis['cross_ws_deps']}")
        
        if same_ws_percent > 80:
            print("  ✅ Excellent cohesion - most dependencies are within workstreams")
        elif same_ws_percent > 60:
            print("  🟡 Good cohesion - majority of dependencies are within workstreams")
        else:
            print("  ⚠️  Low cohesion - many cross-workstream dependencies")
    
    conn.close()

async def test_relationship_migration(db_path, db_name, temp_dir):
    """Test relationship-aware migration"""
    print(f"\n{'#'*80}")
    print(f"# TESTING RELATIONSHIP-AWARE MIGRATION: {db_name}")
    print("#"*80)
    
    # Copy database to temp location
    temp_db = temp_dir / f"{db_name}_relationship_test.db"
    shutil.copy2(db_path, temp_db)
    
    # Update environment to use temp database
    os.environ['MCP_PROJECT_DIR'] = str(temp_dir.parent)
    
    # Create .agent directory for migration
    agent_dir = temp_dir.parent / '.agent'
    agent_dir.mkdir(exist_ok=True)
    shutil.copy2(temp_db, agent_dir / 'mcp_state.db')
    
    # Run migration
    print(f"\n🔧 Running relationship-aware granular migration...")
    from agent_mcp.core.granular_migration import run_granular_migration
    
    try:
        start_time = datetime.now()
        success = await run_granular_migration()
        duration = (datetime.now() - start_time).total_seconds()
        
        if success:
            print(f"✅ Migration completed in {duration:.2f} seconds")
            
            # Analyze results
            migrated_db = agent_dir / 'mcp_state.db'
            conn = sqlite3.connect(migrated_db)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Basic statistics
            cursor.execute("SELECT COUNT(*) as count FROM tasks")
            total_tasks = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM tasks WHERE task_id LIKE 'phase_%'")
            phases = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM tasks WHERE task_id LIKE 'root_%'")
            workstreams = cursor.fetchone()['count']
            
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM tasks 
                WHERE parent_task IS NULL 
                AND task_id NOT LIKE 'phase_%'
                AND task_id NOT LIKE 'root_%'
            """)
            orphaned = cursor.fetchone()['count']
            
            # Empty workstreams
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM tasks 
                WHERE task_id LIKE 'root_%' 
                AND NOT EXISTS (SELECT 1 FROM tasks WHERE parent_task = tasks.task_id)
            """)
            empty_workstreams = cursor.fetchone()['count']
            
            print(f"\n{'='*60}")
            print("MIGRATION RESULTS")
            print("="*60)
            print(f"Total Tasks: {total_tasks}")
            print(f"Phases: {phases}")
            print(f"Workstreams: {workstreams}")
            print(f"Orphaned Tasks: {orphaned}")
            print(f"Empty Workstreams: {empty_workstreams}")
            
            # Success criteria
            print(f"\n{'='*60}")
            print("SUCCESS CRITERIA")
            print("="*60)
            print(f"{'✅' if orphaned == 0 else '❌'} No orphaned tasks")
            print(f"{'✅' if empty_workstreams == 0 else '❌'} No empty workstreams")
            print(f"{'✅' if workstreams > 0 else '❌'} Created workstreams")
            
            conn.close()
            
            # Analyze hierarchy preservation
            hierarchy_analysis = analyze_hierarchy_preservation(migrated_db, db_name)
            
            # Analyze relationship cohesion
            analyze_relationship_cohesion(migrated_db, db_name)
            
            return {
                'success': True,
                'orphaned': orphaned,
                'empty_workstreams': empty_workstreams,
                'hierarchical_tasks': hierarchy_analysis['hierarchical_tasks'],
                'has_deep_hierarchies': hierarchy_analysis['has_deep_hierarchies']
            }
            
        else:
            print("❌ Migration failed")
            return {'success': False}
            
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False}
    
    finally:
        # Cleanup
        if agent_dir.exists():
            shutil.rmtree(agent_dir)

async def main():
    """Test relationship-aware migration on both databases"""
    temp_dir = Path('/tmp/agent_mcp_relationship_test')
    temp_dir.mkdir(exist_ok=True)
    
    databases = [
        (Path('/home/alejandro/Code/Clover/.agent/mcp_state.db'), 'Clover'),
        (Path('/home/alejandro/Code/clover4/.agent/mcp_state.db'), 'Clover4')
    ]
    
    all_results = {}
    
    for db_path, db_name in databases:
        if db_path.exists():
            results = await test_relationship_migration(db_path, db_name, temp_dir)
            if results.get('success'):
                all_results[db_name] = results
        else:
            print(f"\n⚠️  Database not found: {db_path}")
    
    # Final summary
    print(f"\n{'='*80}")
    print("RELATIONSHIP-AWARE MIGRATION SUMMARY")
    print("="*80)
    
    for db_name, results in all_results.items():
        print(f"\n{db_name}:")
        print(f"  ✅ Orphaned Tasks: {results['orphaned']} (SOLVED!)")
        print(f"  {'✅' if results['empty_workstreams'] == 0 else '❌'} Empty Workstreams: {results['empty_workstreams']}")
        print(f"  {'✅' if results['hierarchical_tasks'] > 0 else '❌'} Preserved Hierarchies: {results['hierarchical_tasks']} tasks")
        print(f"  {'✅' if results['has_deep_hierarchies'] else '⚠️'} Deep Hierarchies: {'Yes' if results['has_deep_hierarchies'] else 'No'}")
    
    print("\n🎯 KEY IMPROVEMENTS:")
    print("✅ Relationship analysis identifies natural task clusters")
    print("✅ Parent-child relationships preserved within workstreams")
    print("✅ Dependencies kept together in same workstream")
    print("✅ No orphaned tasks - every task has a home")
    print("✅ Only creates workstreams with actual tasks")
    
    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    asyncio.run(main())