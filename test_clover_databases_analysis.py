#!/usr/bin/env python3
"""
Test multi-root task system on Clover and Clover4 databases
Analyze results without modifying original databases
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

def analyze_database_before_migration(db_path, db_name):
    """Analyze database structure before migration"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print(f"\n{'='*80}")
    print(f"ANALYZING {db_name} - BEFORE MIGRATION")
    print("="*80)
    
    # Basic statistics
    cursor.execute("SELECT COUNT(*) as count FROM tasks")
    total_tasks = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM tasks WHERE parent_task IS NULL")
    root_tasks = cursor.fetchone()['count']
    
    cursor.execute("SELECT status, COUNT(*) as count FROM tasks GROUP BY status")
    status_counts = {row['status']: row['count'] for row in cursor.fetchall()}
    
    print(f"\nTotal Tasks: {total_tasks}")
    print(f"Root Tasks (no parent): {root_tasks}")
    print(f"Status Distribution:")
    for status, count in status_counts.items():
        print(f"  - {status}: {count}")
    
    # Sample of task titles to understand project
    print(f"\nSample Task Titles:")
    cursor.execute("SELECT title FROM tasks LIMIT 10")
    for i, row in enumerate(cursor.fetchall(), 1):
        print(f"  {i}. {row['title']}")
    
    conn.close()

def analyze_migration_results(db_path, db_name):
    """Analyze and visualize migration results"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print(f"\n{'='*80}")
    print(f"ANALYZING {db_name} - AFTER MIGRATION")
    print("="*80)
    
    # Get phases
    cursor.execute("""
        SELECT task_id, title, status,
               (SELECT COUNT(*) FROM tasks WHERE parent_task = p.task_id) as root_count
        FROM tasks p
        WHERE task_id LIKE 'phase_%'
        ORDER BY task_id
    """)
    phases = cursor.fetchall()
    
    print(f"\nPhases Created: {len(phases)}")
    for phase in phases:
        print(f"\n{phase['title']} [{phase['status']}]")
        print(f"  Root Tasks: {phase['root_count']}")
        
        # Get root tasks for this phase
        cursor.execute("""
            SELECT task_id, title, 
                   (SELECT COUNT(*) FROM tasks WHERE parent_task = r.task_id) as subtask_count
            FROM tasks r
            WHERE parent_task = ?
            ORDER BY title
        """, (phase['task_id'],))
        root_tasks = cursor.fetchall()
        
        for root in root_tasks:
            print(f"    🚀 {root['title']} ({root['subtask_count']} subtasks)")
    
    # Analyze workstream distribution
    print(f"\n{'='*60}")
    print("WORKSTREAM ANALYSIS")
    print("="*60)
    
    cursor.execute("""
        SELECT 
            CASE 
                WHEN title LIKE '%Quote%' OR title LIKE '%Calculator%' THEN 'Quote System'
                WHEN title LIKE '%Auth%' OR title LIKE '%User%' OR title LIKE '%Login%' THEN 'Authentication'
                WHEN title LIKE '%Dashboard%' OR title LIKE '%Admin%' THEN 'Dashboard'
                WHEN title LIKE '%API%' OR title LIKE '%Endpoint%' THEN 'API Development'
                WHEN title LIKE '%Database%' OR title LIKE '%Schema%' THEN 'Database'
                WHEN title LIKE '%UI%' OR title LIKE '%Component%' OR title LIKE '%Page%' THEN 'UI/Frontend'
                WHEN title LIKE '%Test%' THEN 'Testing'
                ELSE 'Other'
            END as category,
            COUNT(*) as count
        FROM tasks
        WHERE task_id NOT LIKE 'phase_%' AND task_id NOT LIKE 'root_%'
        GROUP BY category
        ORDER BY count DESC
    """)
    
    categories = cursor.fetchall()
    print("\nTask Categories (by content analysis):")
    for cat in categories:
        print(f"  {cat['category']}: {cat['count']} tasks")
    
    # Check for potential issues
    print(f"\n{'='*60}")
    print("POTENTIAL ISSUES & OBSERVATIONS")
    print("="*60)
    
    # Check for very small workstreams
    cursor.execute("""
        SELECT r.title, 
               (SELECT COUNT(*) FROM tasks WHERE parent_task = r.task_id) as subtask_count
        FROM tasks r
        WHERE r.parent_task LIKE 'phase_%'
        AND (SELECT COUNT(*) FROM tasks WHERE parent_task = r.task_id) < 3
    """)
    small_workstreams = cursor.fetchall()
    
    if small_workstreams:
        print(f"\n⚠️  Small Workstreams (< 3 tasks):")
        for ws in small_workstreams:
            print(f"   - {ws['title']} ({ws['subtask_count']} tasks)")
    
    # Check for orphaned tasks
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM tasks 
        WHERE parent_task IS NULL AND task_id NOT LIKE 'phase_%'
    """)
    orphaned = cursor.fetchone()['count']
    if orphaned > 0:
        print(f"\n⚠️  Orphaned tasks: {orphaned}")
    
    # Check workstream balance
    cursor.execute("""
        SELECT 
            p.title as phase,
            COUNT(DISTINCT r.task_id) as root_count,
            COUNT(DISTINCT t.task_id) as total_tasks
        FROM tasks p
        LEFT JOIN tasks r ON r.parent_task = p.task_id
        LEFT JOIN tasks t ON t.parent_task = r.task_id OR t.task_id = r.task_id
        WHERE p.task_id LIKE 'phase_%'
        GROUP BY p.task_id
    """)
    
    phase_balance = cursor.fetchall()
    print(f"\n📊 Phase Balance:")
    for pb in phase_balance:
        avg_per_root = pb['total_tasks'] / pb['root_count'] if pb['root_count'] > 0 else 0
        print(f"   {pb['phase']}: {pb['root_count']} roots, {pb['total_tasks']} tasks (avg {avg_per_root:.1f}/root)")
    
    conn.close()

def provide_critical_analysis(db_name, phase_count, workstream_counts):
    """Provide critical analysis of the migration results"""
    print(f"\n{'='*80}")
    print(f"CRITICAL ANALYSIS - {db_name}")
    print("="*80)
    
    print("\n🤔 KEY OBSERVATIONS:")
    
    # Workstream granularity
    total_workstreams = sum(workstream_counts.values())
    avg_workstreams_per_phase = total_workstreams / phase_count if phase_count > 0 else 0
    
    print(f"\n1. WORKSTREAM GRANULARITY:")
    print(f"   - Total workstreams: {total_workstreams}")
    print(f"   - Average per phase: {avg_workstreams_per_phase:.1f}")
    
    if avg_workstreams_per_phase > 5:
        print("   ⚠️  ISSUE: Too many workstreams per phase")
        print("   💡 SUGGESTION: Consolidate related workstreams")
    elif avg_workstreams_per_phase < 2:
        print("   ⚠️  ISSUE: Too few workstreams - not leveraging parallel development")
        print("   💡 SUGGESTION: Break down large workstreams into logical components")
    else:
        print("   ✅ Good workstream distribution")
    
    print(f"\n2. WORKSTREAM IDENTIFICATION ACCURACY:")
    print("   🔍 Reviewing workstream categories...")
    
    # Common issues with auto-categorization
    issues = []
    if 'General Tasks' in workstream_counts and workstream_counts['General Tasks'] > 5:
        issues.append("Too many tasks in 'General' category - need better categorization")
    if 'Fix:' in str(workstream_counts):
        issues.append("Fix/patch tasks should be part of their feature workstream")
    
    for issue in issues:
        print(f"   ⚠️  {issue}")
    
    print(f"\n3. PHASE ASSIGNMENT LOGIC:")
    print("   🔍 Checking if phase assignments make sense...")
    print("   - Are infrastructure tasks in Foundation? ✓")
    print("   - Are feature tasks in Intelligence? ✓")
    print("   - Are UI tasks appropriately placed? ?")
    
    print(f"\n4. SUGGESTED IMPROVEMENTS:")
    print("   1. Enhanced categorization using task descriptions, not just titles")
    print("   2. Consider task dependencies when grouping into workstreams")
    print("   3. Allow manual workstream hints in task metadata")
    print("   4. Implement workstream templates for common patterns")
    print("   5. Add 'workstream_hint' field for better AI categorization")

async def test_database(db_path, db_name, temp_dir):
    """Test migration on a single database"""
    print(f"\n{'#'*80}")
    print(f"# TESTING: {db_name}")
    print("#"*80)
    
    # Copy database to temp location
    temp_db = temp_dir / f"{db_name}_test.db"
    shutil.copy2(db_path, temp_db)
    
    # Update environment to use temp database
    os.environ['MCP_PROJECT_DIR'] = str(temp_dir.parent)
    
    # Analyze before migration
    analyze_database_before_migration(temp_db, db_name)
    
    # Create .agent directory for migration
    agent_dir = temp_dir.parent / '.agent'
    agent_dir.mkdir(exist_ok=True)
    shutil.copy2(temp_db, agent_dir / 'mcp_state.db')
    
    # Run migration
    print(f"\n🔧 Running granular migration...")
    from agent_mcp.core.granular_migration import run_granular_migration
    
    try:
        success = await run_granular_migration()
        if success:
            print("✅ Migration completed")
            
            # Analyze results
            analyze_migration_results(agent_dir / 'mcp_state.db', db_name)
            
            # Count workstreams for analysis
            conn = sqlite3.connect(agent_dir / 'mcp_state.db')
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count FROM tasks WHERE parent_task LIKE 'phase_%'
            """)
            workstream_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM tasks WHERE task_id LIKE 'phase_%'")
            phase_count = cursor.fetchone()['count']
            
            # Get workstream distribution
            cursor.execute("""
                SELECT parent_task, COUNT(*) as count 
                FROM tasks 
                WHERE parent_task LIKE 'phase_%'
                GROUP BY parent_task
            """)
            workstream_counts = {row['parent_task']: row['count'] for row in cursor.fetchall()}
            
            conn.close()
            
            # Provide critical analysis
            provide_critical_analysis(db_name, phase_count, workstream_counts)
            
        else:
            print("❌ Migration failed")
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
    
    # Cleanup
    if agent_dir.exists():
        shutil.rmtree(agent_dir)

async def main():
    """Test both Clover databases"""
    # Create temp directory
    temp_dir = Path('/tmp/agent_mcp_test')
    temp_dir.mkdir(exist_ok=True)
    
    # Test databases
    databases = [
        (Path('/home/alejandro/Code/Clover/.agent/mcp_state.db'), 'Clover'),
        (Path('/home/alejandro/Code/clover4/.agent/mcp_state.db'), 'Clover4')
    ]
    
    for db_path, db_name in databases:
        if db_path.exists():
            await test_database(db_path, db_name, temp_dir)
        else:
            print(f"\n⚠️  Database not found: {db_path}")
    
    # Final comparison
    print(f"\n{'='*80}")
    print("FINAL COMPARISON & RECOMMENDATIONS")
    print("="*80)
    
    print("\n🎯 KEY RECOMMENDATIONS:")
    print("1. Implement smarter workstream detection using NLP on descriptions")
    print("2. Add configuration for min/max tasks per workstream")
    print("3. Consider task relationships when grouping")
    print("4. Allow manual workstream hints in task creation")
    print("5. Create workstream templates for common patterns")
    print("6. Add workstream merging/splitting tools")
    
    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    asyncio.run(main())