#!/usr/bin/env python3
"""
Debug empty workstream issue in Clover migration
"""

import sys
import os
import shutil
import sqlite3
import asyncio
import json
from pathlib import Path

# Add agent_mcp to path
sys.path.insert(0, '/home/alejandro/Code/MCP/Agent-MCP')

# Set up environment
os.environ['MCP_PROJECT_DIR'] = '/home/alejandro/Code/MCP/Agent-MCP'

def debug_empty_workstreams():
    """Debug why Clover has empty workstreams"""
    
    # First, let's look at the original Clover database
    clover_db = Path('/home/alejandro/Code/Clover/.agent/mcp_state.db')
    
    if not clover_db.exists():
        print("Clover database not found")
        return
    
    conn = sqlite3.connect(clover_db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("="*80)
    print("DEBUGGING CLOVER EMPTY WORKSTREAMS")
    print("="*80)
    
    # Get all tasks
    cursor.execute("SELECT task_id, title, description, status, parent_task FROM tasks ORDER BY created_at")
    all_tasks = cursor.fetchall()
    
    print(f"\nTotal tasks in Clover: {len(all_tasks)}")
    
    # Group by status
    status_groups = {}
    for task in all_tasks:
        status = task['status']
        if status not in status_groups:
            status_groups[status] = []
        status_groups[status].append(task)
    
    print("\nTasks by status:")
    for status, tasks in status_groups.items():
        print(f"  {status}: {len(tasks)} tasks")
    
    # Check completed tasks
    print("\n\nCOMPLETED TASKS (Foundation phase candidates):")
    print("-"*60)
    for i, task in enumerate(status_groups.get('completed', [])[:10], 1):
        print(f"{i}. {task['title']}")
        if task['description']:
            print(f"   Description: {task['description'][:100]}...")
    
    # Check if tasks have parent relationships
    parent_count = sum(1 for task in all_tasks if task['parent_task'])
    print(f"\n\nTasks with parents: {parent_count}/{len(all_tasks)}")
    
    # Look for specific workstream patterns in completed tasks
    workstream_analysis = {
        'authentication': [],
        'quote_calculator': [],
        'ui_development': [],
        'api_development': [],
        'database': [],
        'general': []
    }
    
    for task in status_groups.get('completed', []):
        title = task['title'].lower()
        description = (task['description'] or '').lower()
        full_text = f"{title} {description}"
        
        categorized = False
        if any(word in full_text for word in ['auth', 'login', 'user', 'profile']):
            workstream_analysis['authentication'].append(task)
            categorized = True
        elif any(word in full_text for word in ['quote', 'calculator', 'pricing']):
            workstream_analysis['quote_calculator'].append(task)
            categorized = True
        elif any(word in full_text for word in ['ui', 'component', 'page', 'interface']):
            workstream_analysis['ui_development'].append(task)
            categorized = True
        elif any(word in full_text for word in ['api', 'endpoint', 'service']):
            workstream_analysis['api_development'].append(task)
            categorized = True
        elif any(word in full_text for word in ['database', 'schema', 'table']):
            workstream_analysis['database'].append(task)
            categorized = True
        
        if not categorized:
            workstream_analysis['general'].append(task)
    
    print("\n\nWORKSTREAM ANALYSIS (Completed Tasks):")
    print("-"*60)
    for ws_name, tasks in workstream_analysis.items():
        if tasks:
            print(f"\n{ws_name.upper()}: {len(tasks)} tasks")
            for task in tasks[:3]:
                print(f"  - {task['title']}")
    
    conn.close()

async def trace_migration_process():
    """Trace the migration process step by step"""
    
    # Create temp copy
    temp_dir = Path('/tmp/clover_debug')
    temp_dir.mkdir(exist_ok=True)
    
    clover_db = Path('/home/alejandro/Code/Clover/.agent/mcp_state.db')
    temp_db = temp_dir / 'mcp_state.db'
    shutil.copy2(clover_db, temp_db)
    
    # Set up environment
    os.environ['MCP_PROJECT_DIR'] = str(temp_dir)
    
    print("\n\n" + "="*80)
    print("TRACING MIGRATION PROCESS")
    print("="*80)
    
    # Import migration components to trace execution
    from agent_mcp.core.granular_migration import (
        Step1_ProjectStateAnalyzer,
        Step2_PhaseCurrentStateMapper,
        Step3_TaskCategorizer,
        Step4_PhaseStructureBuilder
    )
    
    conn = sqlite3.connect(temp_db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Load tasks
    cursor.execute("SELECT * FROM tasks ORDER BY created_at")
    all_tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Step 1: Analyze state
    analyzer = Step1_ProjectStateAnalyzer()
    state_analysis = await analyzer.analyze_current_state(all_tasks)
    
    print("\nStep 1 - State Analysis:")
    print(f"  Completion: {state_analysis['completion_percentage']}%")
    print(f"  Project maturity: {state_analysis['project_maturity']}")
    print(f"  Development stage: {state_analysis['development_stage']}")
    print(f"  Foundation complete: {state_analysis['completed_work']['foundation_complete']}")
    
    # Step 2: Map to phases
    mapper = Step2_PhaseCurrentStateMapper()
    phase_mapping = await mapper.map_to_phases(state_analysis)
    
    print("\nStep 2 - Phase Mapping:")
    print(f"  Current phase: {phase_mapping['current_phase']}")
    print(f"  Completed phases: {phase_mapping['completed_phases']}")
    
    # Step 3: Categorize tasks
    categorizer = Step3_TaskCategorizer()
    task_categorization = await categorizer.categorize_tasks(all_tasks, phase_mapping)
    
    print("\nStep 3 - Task Categorization:")
    for category, tasks in task_categorization.items():
        if tasks and 'tasks' in category:
            print(f"  {category}: {len(tasks)} tasks")
    
    # Step 4: Build structure
    builder = Step4_PhaseStructureBuilder()
    phase_structure = await builder.build_phase_structure(phase_mapping, task_categorization)
    
    print("\nStep 4 - Phase Structure:")
    print(f"  Phases to create: {len(phase_structure['phases_to_create'])}")
    print(f"  Task assignments: {len(phase_structure['task_assignments'])}")
    print(f"  Workstream mappings: {len(phase_structure['workstream_mappings'])}")
    
    # Check workstream mappings detail
    print("\nWorkstream Mappings Detail:")
    for ws_id, ws_info in phase_structure['workstream_mappings'].items():
        print(f"\n  {ws_info['title']}:")
        print(f"    Phase: {ws_info['phase_id']}")
        print(f"    Tasks: {len(ws_info.get('tasks', []))}")
        if ws_info.get('tasks'):
            for task in ws_info['tasks'][:2]:
                print(f"      - {task.get('title', 'No title')}")
    
    # Cleanup
    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    debug_empty_workstreams()
    asyncio.run(trace_migration_process())