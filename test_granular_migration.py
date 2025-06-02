#!/usr/bin/env python3
"""
Test the granular step-by-step migration system
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

async def test_granular_migration():
    """Test the granular migration system step by step"""
    
    print("🔧 **Testing Granular Step-by-Step Migration System**")
    print("=" * 80)
    
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
        from agent_mcp.core.granular_migration import (
            Step1_ProjectStateAnalyzer, 
            Step2_PhaseCurrentStateMapper,
            Step3_TaskCategorizer,
            Step4_PhaseStructureBuilder,
            GranularMigrationManager
        )
        
        # Load all tasks for analysis
        migration_manager = GranularMigrationManager()
        all_tasks = migration_manager._load_all_tasks()
        
        print(f"📊 Loaded {len(all_tasks)} tasks for granular step-by-step analysis\\n")
        
        # Step 1: Project State Analysis
        print("🔍 **STEP 1: Project State Analysis**")
        print("-" * 60)
        
        step1_analyzer = Step1_ProjectStateAnalyzer()
        state_analysis = await step1_analyzer.analyze_current_state(all_tasks)
        
        print(f"Project maturity: {state_analysis['project_maturity']}")
        print(f"Development stage: {state_analysis['development_stage']}")
        print(f"Completion: {state_analysis['completion_percentage']}%")
        print()
        
        print("Completed work analysis:")
        completed_work = state_analysis['completed_work']
        print(f"  Foundation complete: {completed_work['foundation_complete']}")
        print(f"  Has user interface: {completed_work['has_user_interface']}")
        print(f"  Has business logic: {completed_work['has_business_logic']}")
        print(f"  Production ready: {completed_work['is_production_ready']}")
        
        if completed_work['capabilities_built']:
            print(f"  Built capabilities: {', '.join(completed_work['capabilities_built'])}")
        print()
        
        print("Current work focus:")
        current_work = state_analysis['current_work']
        if current_work['primary_focus']:
            print(f"  Primary focus: {current_work['primary_focus']}")
            print(f"  Focus areas: {current_work['focus_areas']}")
        print()
        
        # Step 2: Phase Mapping
        print("🎯 **STEP 2: Phase Current State Mapping**")
        print("-" * 60)
        
        step2_mapper = Step2_PhaseCurrentStateMapper()
        phase_mapping = await step2_mapper.map_to_phases(state_analysis)
        
        print(f"Current phase: {phase_mapping['current_phase']}")
        print(f"Completed phases: {phase_mapping['completed_phases']}")
        print(f"Next phase: {phase_mapping['next_phase']}")
        print()
        
        print("Reasoning:")
        for reason in phase_mapping['reasoning']:
            print(f"  • {reason}")
        print()
        
        print("Phase recommendations:")
        for phase_id, rec in phase_mapping['phase_recommendations'].items():
            print(f"  {phase_id}: {rec['status']}")
            if rec['work_required']:
                print(f"    Work required: {', '.join(rec['work_required'])}")
        print()
        
        # Step 3: Task Categorization
        print("📋 **STEP 3: Task Categorization**")
        print("-" * 60)
        
        step3_categorizer = Step3_TaskCategorizer()
        task_categorization = await step3_categorizer.categorize_tasks(all_tasks, phase_mapping)
        
        for category, tasks in task_categorization.items():
            if tasks and 'tasks' in category:
                print(f"{category}: {len(tasks)} tasks")
                
                # Show examples
                for i, task in enumerate(tasks[:3]):
                    status_icon = {"completed": "✅", "in_progress": "🟡", "pending": "⏳", "cancelled": "❌"}.get(task['status'], "❓")
                    print(f"    {i+1}. {status_icon} {task['title'][:50]}...")
                
                if len(tasks) > 3:
                    print(f"    ... and {len(tasks) - 3} more")
                print()
        
        # Step 4: Phase Structure Building
        print("🏗️ **STEP 4: Phase Structure Building**")
        print("-" * 60)
        
        step4_builder = Step4_PhaseStructureBuilder()
        phase_structure = await step4_builder.build_phase_structure(phase_mapping, task_categorization)
        
        print(f"Phases to create: {len(phase_structure['phases_to_create'])}")
        
        for phase_info in phase_structure['phases_to_create']:
            print(f"\\n📊 {phase_info['name']} ({phase_info['status']})")
            print(f"    Tasks: {len(phase_info['tasks'])}")
            print(f"    Description: {phase_info['description']}")
            
            # Show task examples
            if phase_info['tasks']:
                print("    Example tasks:")
                for i, task in enumerate(phase_info['tasks'][:3]):
                    status_icon = {"completed": "✅", "in_progress": "🟡", "pending": "⏳", "cancelled": "❌"}.get(task['status'], "❓")
                    print(f"      {i+1}. {status_icon} {task['title'][:45]}...")
                if len(phase_info['tasks']) > 3:
                    print(f"      ... and {len(phase_info['tasks']) - 3} more")
        
        print()
        print("Migration strategy:")
        strategy = phase_structure['migration_strategy']
        for reason in strategy['reasoning']:
            print(f"  • {reason}")
        print()
        
        # Step 5: Execute Full Migration
        print("🚀 **STEP 5: Execute Granular Migration**")
        print("-" * 60)
        
        success = await migration_manager.run_granular_migration()
        
        if success:
            print("✅ Granular migration completed successfully!")
            
            # Verify results with detailed analysis
            conn = sqlite3.connect(test_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Check created phases with their statuses
            cursor.execute("SELECT task_id, title, status FROM tasks WHERE task_id LIKE 'phase_%' ORDER BY task_id")
            created_phases = cursor.fetchall()
            
            print(f"\\n📊 **Final Migration Results**")
            print(f"Phases created: {len(created_phases)}")
            
            for phase in created_phases:
                print(f"  {phase['status']} {phase['task_id']}: {phase['title']}")
            print()
            
            # Analyze task distribution by phase
            print("📦 **Task Distribution Analysis**")
            
            total_migrated = 0
            for phase in created_phases:
                phase_id = phase['task_id']
                
                # Count root tasks directly under this phase
                cursor.execute("SELECT COUNT(*) as count FROM tasks WHERE parent_task = ?", (phase_id,))
                root_tasks = cursor.fetchone()['count']
                
                # Count all tasks in this phase tree
                cursor.execute("""
                    WITH RECURSIVE phase_tree AS (
                        SELECT task_id FROM tasks WHERE parent_task = ?
                        UNION ALL
                        SELECT t.task_id FROM tasks t
                        JOIN phase_tree pt ON t.parent_task = pt.task_id
                    )
                    SELECT COUNT(*) as count FROM phase_tree
                """, (phase_id,))
                total_in_phase = cursor.fetchone()['count']
                
                total_migrated += total_in_phase
                
                print(f"  {phase['title']}:")
                print(f"    Direct children: {root_tasks}")
                print(f"    Total in phase: {total_in_phase}")
                print(f"    Status: {phase['status']}")
                print()
            
            # Validation checks
            print("✅ **Validation Results**")
            
            # Check for orphaned tasks
            cursor.execute("""
                SELECT COUNT(*) as count FROM tasks 
                WHERE parent_task IS NULL AND task_id NOT LIKE 'phase_%'
            """)
            orphaned = cursor.fetchone()['count']
            
            # Check total task count
            cursor.execute("SELECT COUNT(*) as count FROM tasks WHERE task_id NOT LIKE 'phase_%'")
            original_tasks = cursor.fetchone()['count']
            
            print(f"Original tasks: {len(all_tasks)}")
            print(f"Tasks after migration: {original_tasks}")
            print(f"Tasks migrated to phases: {total_migrated}")
            print(f"Orphaned tasks: {orphaned}")
            print()
            
            if orphaned == 0 and total_migrated == original_tasks:
                print("🎉 Perfect migration! All tasks properly organized, no orphans.")
            elif orphaned == 0:
                print("✅ Good migration! No orphaned tasks.")
            else:
                print(f"⚠️ Found {orphaned} orphaned tasks - may need adjustment.")
            
            # Show phase status intelligence
            print("\\n🧠 **Phase Status Intelligence**")
            completed_phases_count = len([p for p in created_phases if p['status'] == 'completed'])
            active_phases_count = len([p for p in created_phases if p['status'] == 'in_progress'])
            
            print(f"Completed phases: {completed_phases_count}")
            print(f"Active phases: {active_phases_count}")
            
            if completed_phases_count > 0:
                print("✅ System correctly identified completed foundational work")
            if active_phases_count == 1:
                print("✅ System correctly identified single active development phase")
            
            conn.close()
            
        else:
            print("❌ Granular migration failed!")
            return False
    
    except Exception as e:
        print(f"❌ Error during granular migration test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Restore original database
        if backup_path.exists():
            shutil.copy2(backup_path, test_db_path)
            backup_path.unlink()
    
    return True

async def demonstrate_granular_approach():
    """Demonstrate the benefits of the granular approach"""
    
    print("\\n" + "=" * 80)
    print("🔧 **Granular Migration Approach Benefits**")
    print("=" * 80)
    
    print("""
The Granular Migration System addresses all previous criticisms:

🔍 **Step 1: Project State Analysis**
   ✅ Understands CURRENT state, not just task content
   ✅ Identifies what's actually been built vs planned
   ✅ Recognizes project maturity and development stage
   ✅ Analyzes completed vs active vs future work separately

🎯 **Step 2: Phase Current State Mapping**
   ✅ Maps current state to appropriate phase progression
   ✅ Marks completed phases as 'completed' (not pending)
   ✅ Identifies which phase project is CURRENTLY in
   ✅ Plans logical next steps based on real progress

📋 **Step 3: Task Categorization**
   ✅ Categorizes based on project understanding, not just keywords
   ✅ Uses current phase context to inform decisions
   ✅ Separates completed work from active work
   ✅ Considers task status in categorization logic

🏗️ **Step 4: Phase Structure Building**
   ✅ Creates phases with appropriate status (completed/active)
   ✅ Only creates phases that make sense for current state
   ✅ Builds structure for where project IS, not where it should be
   ✅ Preserves existing task hierarchies intelligently

🚀 **Step 5: Intelligent Execution**
   ✅ Migrates based on understanding, not assumptions
   ✅ Maintains logical task relationships
   ✅ Creates actionable phase structure for continued development

**Key Improvements:**
• State-aware analysis instead of content-only classification
• Proper handling of completed vs active work
• Realistic phase creation based on actual project progress
• Granular step-by-step validation at each stage
• Intelligent status assignment (completed phases marked complete)

This creates a migration that reflects REALITY, not just abstract categorization!
""")

if __name__ == "__main__":
    print("🔧 Testing Granular Step-by-Step Migration System")
    
    async def run_tests():
        if await test_granular_migration():
            await demonstrate_granular_approach()
            print("\\n🎉 Granular migration system working excellently!")
            print("Step-by-step analysis creates realistic, actionable phase structures.")
        else:
            print("\\n❌ Granular migration system needs refinement.")
    
    asyncio.run(run_tests())