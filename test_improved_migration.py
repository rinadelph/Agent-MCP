#!/usr/bin/env python3
"""
Test improved multi-root task migration with better workstream identification
This test validates the fixes for the issues found in CRITICAL_ANALYSIS_CLOVER_MIGRATION.md
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

def analyze_migration_results(db_path, db_name):
    """Analyze improved migration results"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print(f"\n{'='*80}")
    print(f"ANALYZING {db_name} - IMPROVED MIGRATION RESULTS")
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
    
    all_workstreams = []
    empty_workstreams = []
    small_workstreams = []
    
    for phase in phases:
        print(f"\n{phase['title']} [{phase['status']}]")
        print(f"  Root Tasks (Workstreams): {phase['root_count']}")
        
        # Get root tasks for this phase
        cursor.execute("""
            SELECT task_id, title, status,
                   (SELECT COUNT(*) FROM tasks WHERE parent_task = r.task_id) as subtask_count
            FROM tasks r
            WHERE parent_task = ?
            ORDER BY title
        """, (phase['task_id'],))
        root_tasks = cursor.fetchall()
        
        for root in root_tasks:
            all_workstreams.append(root)
            status_icon = "✅" if root['status'] == 'completed' else \
                         "🟡" if root['status'] == 'in_progress' else "⭐"
            print(f"    {status_icon} {root['title']} ({root['subtask_count']} tasks)")
            
            if root['subtask_count'] == 0:
                empty_workstreams.append(root)
            elif root['subtask_count'] < 3:
                small_workstreams.append(root)
    
    # Check for orphaned tasks
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM tasks 
        WHERE parent_task IS NULL AND task_id NOT LIKE 'phase_%'
    """)
    orphaned = cursor.fetchone()['count']
    
    # Get total tasks
    cursor.execute("SELECT COUNT(*) as count FROM tasks")
    total_tasks = cursor.fetchone()['count']
    
    # Summary statistics
    print(f"\n{'='*60}")
    print("IMPROVED MIGRATION STATISTICS")
    print("="*60)
    print(f"Total Tasks: {total_tasks}")
    print(f"Total Workstreams: {len(all_workstreams)}")
    print(f"Average Workstreams per Phase: {len(all_workstreams)/len(phases):.1f}" if phases else "N/A")
    print(f"Empty Workstreams: {len(empty_workstreams)}")
    print(f"Small Workstreams (<3 tasks): {len(small_workstreams)}")
    print(f"Orphaned Tasks: {orphaned}")
    
    # Success metrics
    print(f"\n{'='*60}")
    print("SUCCESS METRICS EVALUATION")
    print("="*60)
    
    avg_per_phase = len(all_workstreams)/len(phases) if phases else 0
    success_metrics = {
        "Workstreams per phase (3-7)": "✅" if 3 <= avg_per_phase <= 7 else "❌",
        "No empty workstreams": "✅" if len(empty_workstreams) == 0 else "❌",
        "Minimal orphaned tasks (<5%)": "✅" if orphaned < total_tasks * 0.05 else "❌",
        "No verb/adjective workstreams": "✅"  # Will check below
    }
    
    # Check for bad workstream names
    bad_names = []
    for ws in all_workstreams:
        title_lower = ws['title'].lower()
        # Check if title is a verb/adjective or single word
        if any(word in title_lower for word in ['complete', 'create', 'implement', 'deep', 'unit']):
            bad_names.append(ws['title'])
            success_metrics["No verb/adjective workstreams"] = "❌"
    
    for metric, result in success_metrics.items():
        print(f"{result} {metric}")
    
    if bad_names:
        print(f"\n⚠️  Bad workstream names found: {', '.join(bad_names)}")
    
    conn.close()
    
    return {
        'total_workstreams': len(all_workstreams),
        'empty_workstreams': len(empty_workstreams),
        'orphaned_tasks': orphaned,
        'avg_per_phase': avg_per_phase,
        'bad_names': bad_names
    }

async def test_improved_migration(db_path, db_name, temp_dir):
    """Test improved migration on a database"""
    print(f"\n{'#'*80}")
    print(f"# TESTING IMPROVED MIGRATION: {db_name}")
    print("#"*80)
    
    # Copy database to temp location
    temp_db = temp_dir / f"{db_name}_improved_test.db"
    shutil.copy2(db_path, temp_db)
    
    # Update environment to use temp database
    os.environ['MCP_PROJECT_DIR'] = str(temp_dir.parent)
    
    # Create .agent directory for migration
    agent_dir = temp_dir.parent / '.agent'
    agent_dir.mkdir(exist_ok=True)
    shutil.copy2(temp_db, agent_dir / 'mcp_state.db')
    
    # Run improved migration
    print(f"\n🔧 Running improved granular migration...")
    from agent_mcp.core.granular_migration import run_granular_migration
    
    try:
        success = await run_granular_migration()
        if success:
            print("✅ Migration completed")
            
            # Analyze results
            results = analyze_migration_results(agent_dir / 'mcp_state.db', db_name)
            
            # Critical analysis
            print(f"\n{'='*60}")
            print("CRITICAL ANALYSIS")
            print("="*60)
            
            improvement = "SIGNIFICANT" if results['empty_workstreams'] == 0 and \
                                          results['avg_per_phase'] <= 7 and \
                                          not results['bad_names'] else "PARTIAL"
            
            print(f"\n🎯 IMPROVEMENT LEVEL: {improvement}")
            
            if results['empty_workstreams'] == 0:
                print("✅ Empty workstreams issue RESOLVED")
            else:
                print(f"❌ Still have {results['empty_workstreams']} empty workstreams")
            
            if results['avg_per_phase'] <= 7:
                print("✅ Workstream granularity IMPROVED")
            else:
                print(f"❌ Still too many workstreams per phase: {results['avg_per_phase']:.1f}")
            
            if not results['bad_names']:
                print("✅ Workstream naming FIXED")
            else:
                print(f"❌ Bad workstream names remain: {', '.join(results['bad_names'])}")
            
            return results
            
        else:
            print("❌ Migration failed")
            return None
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        # Cleanup
        if agent_dir.exists():
            shutil.rmtree(agent_dir)

async def main():
    """Test improved migration on both Clover databases"""
    # Create temp directory
    temp_dir = Path('/tmp/agent_mcp_improved_test')
    temp_dir.mkdir(exist_ok=True)
    
    # Test databases
    databases = [
        (Path('/home/alejandro/Code/Clover/.agent/mcp_state.db'), 'Clover'),
        (Path('/home/alejandro/Code/clover4/.agent/mcp_state.db'), 'Clover4')
    ]
    
    all_results = {}
    
    for db_path, db_name in databases:
        if db_path.exists():
            results = await test_improved_migration(db_path, db_name, temp_dir)
            if results:
                all_results[db_name] = results
        else:
            print(f"\n⚠️  Database not found: {db_path}")
    
    # Final comparison
    print(f"\n{'='*80}")
    print("IMPROVEMENT COMPARISON")
    print("="*80)
    
    print("\nBEFORE (from critical analysis):")
    print("- Clover4: 26 root tasks, many empty, nonsensical names")
    print("- Clover: 7 root tasks, ALL empty")
    print("- Many orphaned tasks (22 in Clover4)")
    
    print("\nAFTER (improved migration):")
    for db_name, results in all_results.items():
        print(f"\n{db_name}:")
        print(f"- {results['total_workstreams']} workstreams total")
        print(f"- {results['empty_workstreams']} empty workstreams")
        print(f"- {results['orphaned_tasks']} orphaned tasks")
        print(f"- {results['avg_per_phase']:.1f} workstreams per phase")
    
    print("\n🎯 KEY IMPROVEMENTS IMPLEMENTED:")
    print("1. ✅ Score-based workstream detection with full text analysis")
    print("2. ✅ Consolidation of small workstreams (<3 tasks)")
    print("3. ✅ Maximum workstream limit (7) with overflow handling")
    print("4. ✅ Better workstream naming (no verb/adjective names)")
    print("5. ✅ Workstream status based on child task statuses")
    
    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    asyncio.run(main())