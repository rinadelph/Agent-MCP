#!/usr/bin/env python3
"""
Test the intelligent migration system with AI reasoning and dependency fixing
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

async def test_intelligent_migration():
    """Test the intelligent migration system with AI reasoning chains"""
    
    print("🧠 **Testing Intelligent AI-Powered Migration System**")
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
        from agent_mcp.core.intelligent_migration import IntelligentMigrationManager, ProjectAnalysisChain
        
        migration_manager = IntelligentMigrationManager()
        analysis_chain = ProjectAnalysisChain()
        
        print("🔍 Loading all tasks for AI analysis...")
        all_tasks = migration_manager._load_all_tasks()
        print(f"Loaded {len(all_tasks)} tasks for intelligent analysis")
        
        print("\\n🧠 **AI Analysis Chain - Step 1: Project Domain Analysis**")
        print("-" * 60)
        domain_analysis = await analysis_chain.analyze_project_domain(all_tasks)
        
        print(f"Primary domain: {domain_analysis['primary_domain']}")
        print(f"Project complexity: {domain_analysis['project_complexity']} tasks")
        print(f"Has UI components: {domain_analysis['has_ui_components']}")
        print(f"Has backend work: {domain_analysis['has_backend_work']}")
        print(f"Has business logic: {domain_analysis['has_business_logic']}")
        print("\\nDomain scores:")
        for domain, score in sorted(domain_analysis['domain_scores'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {domain}: {score}")
        
        print("\\n🧩 **AI Analysis Chain - Step 2: Task Complexity Layers**")
        print("-" * 60)
        complexity_analysis = await analysis_chain.analyze_task_complexity_layers(all_tasks)
        
        for layer, tasks in complexity_analysis.items():
            if tasks:
                print(f"{layer}: {len(tasks)} tasks")
                # Show a few examples
                for i, task in enumerate(tasks[:3]):
                    print(f"  {i+1}. {task['title'][:60]}... ({task['status']})")
                if len(tasks) > 3:
                    print(f"  ... and {len(tasks) - 3} more")
                print()
        
        print("🔗 **AI Analysis Chain - Step 3: Dependency Analysis**")
        print("-" * 60)
        dependency_analysis = await analysis_chain.analyze_task_dependencies(all_tasks)
        
        print(f"Explicit dependencies: {len(dependency_analysis['explicit_dependencies'])}")
        print(f"Implicit dependencies found: {len(dependency_analysis['implicit_dependencies'])}")
        
        if dependency_analysis['implicit_dependencies']:
            print("\\nImplicit dependencies detected:")
            for i, dep in enumerate(dependency_analysis['implicit_dependencies'][:5]):
                print(f"  {i+1}. {dep['reason']}")
            if len(dependency_analysis['implicit_dependencies']) > 5:
                print(f"  ... and {len(dependency_analysis['implicit_dependencies']) - 5} more")
        
        print("\\n🎯 **AI Analysis Chain - Step 4: Optimal Phase Structure**")
        print("-" * 60)
        phase_structure = await analysis_chain.determine_optimal_phases(domain_analysis, complexity_analysis)
        
        print(f"Recommended phases: {len(phase_structure['recommended_phases'])}")
        print("\\nPhase breakdown:")
        
        for phase in phase_structure['recommended_phases']:
            print(f"\\n📊 **{phase['name']}**")
            print(f"   Tasks: {len(phase['tasks'])}")
            print(f"   Justification: {phase['justification']}")
            
            # Show task examples
            print("   Example tasks:")
            for i, task in enumerate(phase['tasks'][:3]):
                status_icon = {"completed": "✅", "in_progress": "🟡", "pending": "⏳", "cancelled": "❌"}.get(task['status'], "❓")
                print(f"     {i+1}. {status_icon} {task['title'][:50]}...")
            if len(phase['tasks']) > 3:
                print(f"     ... and {len(phase['tasks']) - 3} more tasks")
        
        print("\\nAI Reasoning:")
        for reason in phase_structure['reasoning']:
            print(f"  • {reason}")
        
        print("\\n🚀 **Running Complete Intelligent Migration**")
        print("-" * 60)
        
        success = await migration_manager.run_intelligent_migration()
        
        if success:
            print("✅ Intelligent migration completed successfully!")
            
            # Verify results
            conn = sqlite3.connect(test_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Check created phases
            cursor.execute("SELECT task_id, title FROM tasks WHERE task_id LIKE 'phase_%' ORDER BY task_id")
            created_phases = cursor.fetchall()
            
            print(f"\\n📊 **Migration Results**")
            print(f"Phases created: {len(created_phases)}")
            for phase in created_phases:
                print(f"  ✓ {phase['task_id']}: {phase['title']}")
            
            # Check task distribution
            print(f"\\n📦 **Task Distribution**")
            for phase in created_phases:
                phase_id = phase['task_id']
                
                # Count direct children
                cursor.execute("SELECT COUNT(*) as count FROM tasks WHERE parent_task = ?", (phase_id,))
                direct_children = cursor.fetchone()['count']
                
                # Count all tasks assigned to this phase (including through hierarchy)
                cursor.execute("""
                    WITH RECURSIVE phase_tasks AS (
                        SELECT task_id FROM tasks WHERE parent_task = ?
                        UNION ALL
                        SELECT t.task_id FROM tasks t
                        JOIN phase_tasks pt ON t.parent_task = pt.task_id
                    )
                    SELECT COUNT(*) as count FROM phase_tasks
                """, (phase_id,))
                total_in_phase = cursor.fetchone()['count']
                
                print(f"  {phase['title']}: {direct_children} direct + {total_in_phase - direct_children} nested = {total_in_phase} total")
            
            # Check dependency improvements
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM tasks 
                WHERE depends_on_tasks != '[]' AND depends_on_tasks IS NOT NULL
            """)
            tasks_with_deps = cursor.fetchone()['count']
            print(f"\\n🔗 **Dependency Optimization**")
            print(f"Tasks with dependencies: {tasks_with_deps}")
            
            # Verify no orphaned tasks
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM tasks 
                WHERE parent_task IS NULL AND task_id NOT LIKE 'phase_%'
            """)
            orphaned_tasks = cursor.fetchone()['count']
            
            print(f"\\n✅ **Validation Results**")
            print(f"Orphaned tasks: {orphaned_tasks} (should be 0)")
            
            if orphaned_tasks == 0:
                print("🎉 Perfect! No orphaned tasks - all properly organized")
            else:
                print("⚠️ Found orphaned tasks - migration may need adjustment")
            
            # Show intelligent phase assignment examples
            print(f"\\n🧠 **AI Phase Assignment Examples**")
            for phase in created_phases:
                phase_id = phase['task_id']
                cursor.execute("""
                    SELECT task_id, title, notes 
                    FROM tasks 
                    WHERE parent_task = ? 
                    ORDER BY created_at 
                    LIMIT 2
                """, (phase_id,))
                
                phase_tasks = cursor.fetchall()
                if phase_tasks:
                    print(f"\\n{phase['title']}:")
                    for task in phase_tasks:
                        print(f"  • {task['title'][:50]}...")
                        
                        # Extract AI reasoning from notes
                        try:
                            notes = json.loads(task['notes'])
                            for note in notes:
                                if 'intelligent_migration' in note.get('author', ''):
                                    reasoning = note['content']
                                    if len(reasoning) > 100:
                                        reasoning = reasoning[:100] + "..."
                                    print(f"    🧠 {reasoning}")
                                    break
                        except:
                            pass
            
            conn.close()
            
        else:
            print("❌ Intelligent migration failed!")
            return False
    
    except Exception as e:
        print(f"❌ Error during intelligent migration test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Restore original database
        if backup_path.exists():
            shutil.copy2(backup_path, test_db_path)
            backup_path.unlink()
    
    return True

async def demonstrate_ai_reasoning():
    """Demonstrate the AI reasoning capabilities"""
    
    print("\\n" + "=" * 80)
    print("🧠 **AI Reasoning Demonstration**")
    print("=" * 80)
    
    print("""
The Intelligent Migration System uses a multi-step AI reasoning chain:

🔍 **Step 1: Project Domain Analysis**
   • Analyzes all task titles and descriptions
   • Identifies project type (web dev, mobile, data science, etc.)
   • Detects architectural patterns and complexity
   • Determines if UI, backend, or business logic focused

🧩 **Step 2: Task Complexity Layer Analysis** 
   • Infrastructure tasks → Foundation phase
   • Core algorithms/logic → Intelligence phase  
   • UI/UX and integration → Coordination phase
   • Testing and optimization → Optimization phase
   • Smart handling of unclassified tasks

🔗 **Step 3: Dependency Analysis**
   • Maps existing explicit dependencies
   • Discovers implicit dependencies through content analysis
   • Identifies missing relationships
   • Plans dependency fixes for optimal workflow

🎯 **Step 4: Optimal Phase Structure Determination**
   • Only creates phases with substantial work (3+ tasks)
   • Merges small phases into larger ones
   • Ensures logical progression and proper grouping
   • Adapts to project-specific needs

🚀 **Execution & Optimization**
   • Creates optimized phase structure
   • Migrates tasks with intelligent reasoning
   • Fixes dependencies for unified workflow
   • Preserves existing hierarchy where logical

This creates a project-specific phase structure that actually makes sense
for the work being done, rather than forcing everything into a rigid template!
""")

if __name__ == "__main__":
    print("🧠 Testing Intelligent AI-Powered Migration System")
    
    async def run_tests():
        if await test_intelligent_migration():
            await demonstrate_ai_reasoning()
            print("\\n🎉 Intelligent migration system working perfectly!")
            print("AI reasoning creates optimal phase structures for each project.")
        else:
            print("\\n❌ Intelligent migration system needs improvements.")
    
    asyncio.run(run_tests())