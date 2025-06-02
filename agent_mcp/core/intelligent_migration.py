#!/usr/bin/env python3
"""
Intelligent Multi-Phase Migration System for Agent MCP

This system uses advanced AI reasoning chains to analyze the complete project,
understand task relationships, fix dependencies, and create a proper phase structure.
"""

import json
import sqlite3
import datetime
import asyncio
from typing import Dict, List, Any, Optional, Set, Tuple
from .config import logger
from ..db.connection import get_db_connection


class ProjectAnalysisChain:
    """Multi-step AI analysis chain for understanding the complete project structure"""
    
    def __init__(self):
        self.all_tasks = []
        self.task_map = {}
        self.analysis_results = {}
    
    async def analyze_project_domain(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Step 1: Understand what type of project this is"""
        
        # Analyze task titles and descriptions to understand project domain
        all_text = []
        for task in tasks:
            text = f"{task.get('title', '')} {task.get('description', '')}"
            all_text.append(text.lower())
        
        combined_text = " ".join(all_text)
        
        # Domain detection keywords
        domain_indicators = {
            'web_development': ['website', 'page', 'ui', 'frontend', 'component', 'react', 'vue', 'angular', 'html', 'css', 'javascript'],
            'backend_development': ['api', 'server', 'database', 'auth', 'authentication', 'endpoint', 'service', 'backend'],
            'mobile_development': ['mobile', 'app', 'ios', 'android', 'react native', 'flutter', 'swift', 'kotlin'],
            'data_science': ['data', 'analytics', 'ml', 'machine learning', 'model', 'analysis', 'visualization'],
            'devops': ['deployment', 'ci/cd', 'docker', 'kubernetes', 'infrastructure', 'monitoring'],
            'business_application': ['dashboard', 'crm', 'quote', 'customer', 'business', 'management', 'workflow']
        }
        
        domain_scores = {}
        for domain, keywords in domain_indicators.items():
            score = sum(1 for keyword in keywords if keyword in combined_text)
            domain_scores[domain] = score
        
        primary_domain = max(domain_scores, key=domain_scores.get)
        
        return {
            'primary_domain': primary_domain,
            'domain_scores': domain_scores,
            'project_complexity': len(tasks),
            'has_ui_components': any('component' in task.get('title', '').lower() for task in tasks),
            'has_backend_work': any(keyword in combined_text for keyword in ['api', 'database', 'server']),
            'has_business_logic': any(keyword in combined_text for keyword in ['quote', 'calculator', 'business', 'workflow'])
        }
    
    async def analyze_task_complexity_layers(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Step 2: Identify different complexity layers and architectural components"""
        
        complexity_analysis = {
            'infrastructure_tasks': [],
            'core_functionality_tasks': [],
            'user_interface_tasks': [],
            'integration_tasks': [],
            'optimization_tasks': [],
            'unclassified_tasks': []
        }
        
        for task in tasks:
            title = task.get('title', '').lower()
            description = task.get('description', '').lower()
            status = task.get('status', '')
            
            task_text = f"{title} {description}"
            
            # Infrastructure layer (Foundation)
            if any(keyword in task_text for keyword in [
                'setup', 'config', 'install', 'database', 'schema', 'auth', 'authentication',
                'environment', 'deployment', 'infrastructure', 'basic', 'core setup'
            ]):
                complexity_analysis['infrastructure_tasks'].append(task)
            
            # Core functionality (Intelligence)
            elif any(keyword in task_text for keyword in [
                'calculator', 'algorithm', 'logic', 'processing', 'computation', 'smart',
                'intelligent', 'analysis', 'recommendation', 'search', 'filter'
            ]):
                complexity_analysis['core_functionality_tasks'].append(task)
            
            # User interface (Coordination)
            elif any(keyword in task_text for keyword in [
                'ui', 'interface', 'component', 'page', 'form', 'button', 'modal',
                'styling', 'design', 'layout', 'responsive', 'user experience'
            ]):
                complexity_analysis['user_interface_tasks'].append(task)
            
            # Integration (Coordination)
            elif any(keyword in task_text for keyword in [
                'integration', 'api', 'service', 'workflow', 'coordination', 'communication',
                'synchronization', 'orchestration', 'pipeline'
            ]):
                complexity_analysis['integration_tasks'].append(task)
            
            # Optimization (Optimization)
            elif any(keyword in task_text for keyword in [
                'optimization', 'performance', 'improve', 'enhance', 'polish', 'refine',
                'testing', 'quality', 'monitoring', 'analytics', 'reporting'
            ]):
                complexity_analysis['optimization_tasks'].append(task)
            
            else:
                complexity_analysis['unclassified_tasks'].append(task)
        
        return complexity_analysis
    
    async def analyze_task_dependencies(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Step 3: Understand existing dependencies and identify missing ones"""
        
        dependency_analysis = {
            'explicit_dependencies': {},
            'implicit_dependencies': [],
            'missing_dependencies': [],
            'dependency_violations': [],
            'suggested_fixes': []
        }
        
        # Build task map for quick lookup
        task_map = {task['task_id']: task for task in tasks}
        
        # Analyze explicit dependencies
        for task in tasks:
            task_id = task['task_id']
            depends_on = task.get('depends_on_tasks', '[]')
            
            if isinstance(depends_on, str):
                try:
                    depends_on = json.loads(depends_on)
                except:
                    depends_on = []
            
            dependency_analysis['explicit_dependencies'][task_id] = depends_on
        
        # Identify implicit dependencies through content analysis
        for task in tasks:
            task_title = task.get('title', '').lower()
            
            # Check for implicit dependencies
            for other_task in tasks:
                if task['task_id'] == other_task['task_id']:
                    continue
                
                other_title = other_task.get('title', '').lower()
                
                # Detect implicit dependency patterns
                if self._should_depend_on(task_title, other_title):
                    dependency_analysis['implicit_dependencies'].append({
                        'dependent': task['task_id'],
                        'dependency': other_task['task_id'],
                        'reason': f"'{task_title}' likely depends on '{other_title}'"
                    })
        
        return dependency_analysis
    
    def _should_depend_on(self, task_title: str, potential_dependency_title: str) -> bool:
        """Determine if one task should depend on another based on content"""
        
        dependency_patterns = [
            # UI depends on backend
            ('component', 'api'),
            ('form', 'service'),
            ('page', 'database'),
            
            # Testing depends on implementation
            ('test', 'implement'),
            ('testing', 'feature'),
            
            # Advanced features depend on basic ones
            ('advanced', 'basic'),
            ('enhancement', 'core'),
            ('optimization', 'implementation'),
            
            # Integration depends on components
            ('integration', 'component'),
            ('workflow', 'service'),
        ]
        
        for dependent_keyword, dependency_keyword in dependency_patterns:
            if dependent_keyword in task_title and dependency_keyword in potential_dependency_title:
                return True
        
        return False
    
    async def determine_optimal_phases(self, domain_analysis: Dict[str, Any], 
                                     complexity_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Step 4: Determine optimal phase structure based on project analysis"""
        
        phase_structure = {
            'recommended_phases': [],
            'phase_assignments': {},
            'reasoning': []
        }
        
        primary_domain = domain_analysis['primary_domain']
        project_complexity = domain_analysis['project_complexity']
        
        # Always include Foundation phase
        foundation_tasks = complexity_analysis['infrastructure_tasks'].copy()
        
        # Determine if Intelligence phase is needed
        intelligence_tasks = complexity_analysis['core_functionality_tasks'].copy()
        
        # Coordination phase for UI and integration
        coordination_tasks = (complexity_analysis['user_interface_tasks'] + 
                            complexity_analysis['integration_tasks'])
        
        # Optimization phase
        optimization_tasks = complexity_analysis['optimization_tasks'].copy()
        
        # Handle unclassified tasks intelligently
        unclassified = complexity_analysis['unclassified_tasks']
        
        # Smart assignment of unclassified tasks
        for task in unclassified:
            status = task.get('status', '')
            title = task.get('title', '').lower()
            
            # Completed tasks likely foundational
            if status == 'completed':
                foundation_tasks.append(task)
            # Page/UI related goes to coordination
            elif any(keyword in title for keyword in ['page', 'ui', 'interface', 'component']):
                coordination_tasks.append(task)
            # Default to foundation
            else:
                foundation_tasks.append(task)
        
        # Decide which phases to create based on task distribution
        if foundation_tasks:
            phase_structure['recommended_phases'].append({
                'phase_id': 'phase_1_foundation',
                'name': 'Phase 1: Foundation',
                'tasks': foundation_tasks,
                'justification': f"Core infrastructure and setup tasks ({len(foundation_tasks)} tasks)"
            })
            
            for task in foundation_tasks:
                phase_structure['phase_assignments'][task['task_id']] = 'phase_1_foundation'
        
        if intelligence_tasks and len(intelligence_tasks) >= 3:  # Only create if substantial work
            phase_structure['recommended_phases'].append({
                'phase_id': 'phase_2_intelligence',
                'name': 'Phase 2: Intelligence',
                'tasks': intelligence_tasks,
                'justification': f"Core business logic and intelligent features ({len(intelligence_tasks)} tasks)"
            })
            
            for task in intelligence_tasks:
                phase_structure['phase_assignments'][task['task_id']] = 'phase_2_intelligence'
        else:
            # Merge intelligence tasks into foundation
            foundation_tasks.extend(intelligence_tasks)
            for task in intelligence_tasks:
                phase_structure['phase_assignments'][task['task_id']] = 'phase_1_foundation'
        
        if coordination_tasks and len(coordination_tasks) >= 5:  # Substantial UI/integration work
            phase_structure['recommended_phases'].append({
                'phase_id': 'phase_3_coordination',
                'name': 'Phase 3: Coordination',
                'tasks': coordination_tasks,
                'justification': f"User interface and system integration ({len(coordination_tasks)} tasks)"
            })
            
            for task in coordination_tasks:
                phase_structure['phase_assignments'][task['task_id']] = 'phase_3_coordination'
        else:
            # Merge coordination tasks into foundation or intelligence
            target_phase = 'phase_2_intelligence' if intelligence_tasks else 'phase_1_foundation'
            for task in coordination_tasks:
                phase_structure['phase_assignments'][task['task_id']] = target_phase
        
        if optimization_tasks and len(optimization_tasks) >= 2:  # Any optimization work
            phase_structure['recommended_phases'].append({
                'phase_id': 'phase_4_optimization',
                'name': 'Phase 4: Optimization',
                'tasks': optimization_tasks,
                'justification': f"Performance, testing, and production readiness ({len(optimization_tasks)} tasks)"
            })
            
            for task in optimization_tasks:
                phase_structure['phase_assignments'][task['task_id']] = 'phase_4_optimization'
        else:
            # Merge optimization tasks into highest available phase
            available_phases = [p['phase_id'] for p in phase_structure['recommended_phases']]
            target_phase = available_phases[-1] if available_phases else 'phase_1_foundation'
            for task in optimization_tasks:
                phase_structure['phase_assignments'][task['task_id']] = target_phase
        
        # Add reasoning
        phase_structure['reasoning'] = [
            f"Project domain: {primary_domain}",
            f"Total tasks: {project_complexity}",
            f"Recommended phases: {len(phase_structure['recommended_phases'])}",
            f"Phase distribution ensures logical progression and proper task grouping"
        ]
        
        return phase_structure


class IntelligentMigrationManager:
    """Manages intelligent multi-phase migration with AI reasoning"""
    
    def __init__(self):
        self.analysis_chain = ProjectAnalysisChain()
        self.migration_plan = {}
    
    async def run_intelligent_migration(self) -> bool:
        """Run the complete intelligent migration process"""
        try:
            logger.info("🧠 Starting intelligent multi-phase migration with AI reasoning...")
            
            # Step 1: Check if migration is needed
            if not self._needs_migration():
                return True
            
            # Step 2: Load and prepare all tasks
            logger.info("📊 Loading complete task hierarchy...")
            all_tasks = self._load_all_tasks()
            
            if not all_tasks:
                logger.info("ℹ️ No tasks found to migrate")
                return True
            
            logger.info(f"📋 Loaded {len(all_tasks)} tasks for intelligent analysis")
            
            # Step 3: Multi-step AI analysis chain
            logger.info("🔍 Step 1: Analyzing project domain...")
            domain_analysis = await self.analysis_chain.analyze_project_domain(all_tasks)
            logger.info(f"   Primary domain: {domain_analysis['primary_domain']}")
            logger.info(f"   Project complexity: {domain_analysis['project_complexity']} tasks")
            
            logger.info("🧩 Step 2: Analyzing task complexity layers...")
            complexity_analysis = await self.analysis_chain.analyze_task_complexity_layers(all_tasks)
            
            for layer, tasks in complexity_analysis.items():
                if tasks:
                    logger.info(f"   {layer}: {len(tasks)} tasks")
            
            logger.info("🔗 Step 3: Analyzing task dependencies...")
            dependency_analysis = await self.analysis_chain.analyze_task_dependencies(all_tasks)
            logger.info(f"   Explicit dependencies: {len(dependency_analysis['explicit_dependencies'])}")
            logger.info(f"   Implicit dependencies found: {len(dependency_analysis['implicit_dependencies'])}")
            
            logger.info("🎯 Step 4: Determining optimal phase structure...")
            phase_structure = await self.analysis_chain.determine_optimal_phases(
                domain_analysis, complexity_analysis
            )
            
            logger.info(f"   Recommended phases: {len(phase_structure['recommended_phases'])}")
            for phase in phase_structure['recommended_phases']:
                logger.info(f"   - {phase['name']}: {len(phase['tasks'])} tasks")
                logger.info(f"     Justification: {phase['justification']}")
            
            # Step 4: Create phases and migrate tasks
            logger.info("🚀 Creating phases and migrating tasks...")
            migration_success = await self._execute_migration(phase_structure, dependency_analysis)
            
            if migration_success:
                # Step 5: Fix dependencies
                logger.info("🔧 Fixing and optimizing task dependencies...")
                await self._fix_dependencies(dependency_analysis, phase_structure)
                
                # Step 6: Update migration status
                self._update_migration_status({
                    'total_tasks': len(all_tasks),
                    'phases_created': len(phase_structure['recommended_phases']),
                    'domain_analysis': domain_analysis,
                    'phase_structure': phase_structure
                })
                
                logger.info("✅ Intelligent migration completed successfully!")
                logger.info(f"   🎯 Created {len(phase_structure['recommended_phases'])} optimized phases")
                logger.info(f"   📦 Migrated {len(all_tasks)} tasks with intelligent phase assignment")
                logger.info(f"   🔗 Fixed dependencies for optimal workflow")
                
                return True
            else:
                logger.error("❌ Migration execution failed")
                return False
                
        except Exception as e:
            logger.error(f"Critical error during intelligent migration: {e}")
            return False
    
    def _needs_migration(self) -> bool:
        """Check if intelligent migration is needed"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as count FROM tasks WHERE task_id LIKE 'phase_%'")
            phase_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM tasks")
            total_tasks = cursor.fetchone()['count']
            
            conn.close()
            
            return phase_count == 0 and total_tasks > 0
            
        except Exception as e:
            logger.error(f"Error checking migration status: {e}")
            return False
    
    def _load_all_tasks(self) -> List[Dict[str, Any]]:
        """Load all tasks from database"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM tasks ORDER BY created_at")
            all_tasks = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return all_tasks
            
        except Exception as e:
            logger.error(f"Error loading tasks: {e}")
            return []
    
    async def _execute_migration(self, phase_structure: Dict[str, Any], 
                               dependency_analysis: Dict[str, Any]) -> bool:
        """Execute the migration plan"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Create phases
            for phase in phase_structure['recommended_phases']:
                await self._create_phase(cursor, phase)
            
            # Migrate tasks to phases
            migrated_count = 0
            for task_id, phase_id in phase_structure['phase_assignments'].items():
                if await self._migrate_task_to_phase(cursor, task_id, phase_id, phase_structure):
                    migrated_count += 1
            
            conn.commit()
            conn.close()
            
            logger.info(f"📦 Successfully migrated {migrated_count} tasks to phases")
            return True
            
        except Exception as e:
            logger.error(f"Error executing migration: {e}")
            return False
    
    async def _create_phase(self, cursor, phase_info: Dict[str, Any]) -> None:
        """Create a single phase"""
        phase_id = phase_info['phase_id']
        phase_name = phase_info['name']
        justification = phase_info['justification']
        task_count = len(phase_info['tasks'])
        
        # Check if phase already exists
        cursor.execute("SELECT task_id FROM tasks WHERE task_id = ?", (phase_id,))
        if cursor.fetchone():
            return
        
        created_at = datetime.datetime.now().isoformat()
        
        # Create phase with intelligent description
        phase_definitions = {
            'phase_1_foundation': "Core system architecture, database, authentication, and basic APIs",
            'phase_2_intelligence': "RAG system, embeddings, context management, and AI integration", 
            'phase_3_coordination': "Multi-agent workflows, task orchestration, and system integration",
            'phase_4_optimization': "Performance tuning, scaling, monitoring, and production readiness"
        }
        
        description = phase_definitions.get(phase_id, "Intelligent phase assignment")
        description += f"\n\n🧠 AI Analysis: {justification}"
        
        initial_notes = [{
            "timestamp": created_at,
            "author": "intelligent_migration",
            "content": f"🧠 Intelligent migration: Phase created through AI analysis. {justification}. {task_count} tasks assigned based on content analysis and dependency reasoning."
        }]
        
        phase_data = {
            "task_id": phase_id,
            "title": phase_name,
            "description": description,
            "assigned_to": None,
            "created_by": "intelligent_migration",
            "status": "pending", 
            "priority": "high",
            "created_at": created_at,
            "updated_at": created_at,
            "parent_task": None,
            "child_tasks": json.dumps([]),
            "depends_on_tasks": json.dumps([]),
            "notes": json.dumps(initial_notes)
        }
        
        cursor.execute("""
            INSERT INTO tasks (task_id, title, description, assigned_to, created_by, status, priority,
                             created_at, updated_at, parent_task, child_tasks, depends_on_tasks, notes)
            VALUES (:task_id, :title, :description, :assigned_to, :created_by, :status, :priority,
                    :created_at, :updated_at, :parent_task, :child_tasks, :depends_on_tasks, :notes)
        """, phase_data)
        
        logger.info(f"📊 Created {phase_name}: {justification}")
    
    async def _migrate_task_to_phase(self, cursor, task_id: str, phase_id: str, 
                                   phase_structure: Dict[str, Any]) -> bool:
        """Migrate a single task to its assigned phase"""
        try:
            # Get current task
            cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            task = cursor.fetchone()
            if not task:
                return False
            
            task = dict(task)
            
            updated_at = datetime.datetime.now().isoformat()
            
            # Determine migration strategy based on current parent
            current_parent = task.get('parent_task')
            
            if current_parent is None:
                # Root task - becomes child of phase
                new_parent = phase_id
                migration_type = "root_to_phase"
            else:
                # Subtask - check if parent is also being migrated to same phase
                parent_phase = phase_structure['phase_assignments'].get(current_parent)
                if parent_phase == phase_id:
                    # Parent in same phase - keep existing relationship
                    new_parent = current_parent
                    migration_type = "hierarchy_preserved"
                else:
                    # Parent in different phase - becomes direct child of phase
                    new_parent = phase_id
                    migration_type = "orphan_to_phase"
            
            # Add intelligent migration note
            current_notes = json.loads(task.get('notes', '[]'))
            
            # Find which phase info this belongs to
            phase_info = None
            for phase in phase_structure['recommended_phases']:
                if phase['phase_id'] == phase_id:
                    phase_info = phase
                    break
            
            justification = phase_info['justification'] if phase_info else "Intelligent analysis"
            
            migration_note = {
                "timestamp": updated_at,
                "author": "intelligent_migration",
                "content": f"🧠 Intelligent migration: Assigned to {phase_id} based on AI analysis. {justification}. Migration type: {migration_type}."
            }
            current_notes.append(migration_note)
            
            # Update task
            cursor.execute("""
                UPDATE tasks 
                SET parent_task = ?, updated_at = ?, notes = ?
                WHERE task_id = ?
            """, (new_parent, updated_at, json.dumps(current_notes), task_id))
            
            return True
            
        except Exception as e:
            logger.error(f"Error migrating task {task_id}: {e}")
            return False
    
    async def _fix_dependencies(self, dependency_analysis: Dict[str, Any], 
                              phase_structure: Dict[str, Any]) -> None:
        """Fix and optimize task dependencies"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            fixed_count = 0
            
            # Add missing implicit dependencies
            for implicit_dep in dependency_analysis['implicit_dependencies']:
                dependent_id = implicit_dep['dependent']
                dependency_id = implicit_dep['dependency']
                reason = implicit_dep['reason']
                
                # Get current dependencies
                cursor.execute("SELECT depends_on_tasks FROM tasks WHERE task_id = ?", (dependent_id,))
                result = cursor.fetchone()
                if not result:
                    continue
                
                current_deps = json.loads(result['depends_on_tasks'] or '[]')
                
                # Add dependency if not already present
                if dependency_id not in current_deps:
                    current_deps.append(dependency_id)
                    
                    cursor.execute("""
                        UPDATE tasks 
                        SET depends_on_tasks = ?, updated_at = ?
                        WHERE task_id = ?
                    """, (json.dumps(current_deps), datetime.datetime.now().isoformat(), dependent_id))
                    
                    fixed_count += 1
                    logger.info(f"🔗 Fixed dependency: {dependent_id} → {dependency_id} ({reason})")
            
            conn.commit()
            conn.close()
            
            if fixed_count > 0:
                logger.info(f"✅ Fixed {fixed_count} task dependencies")
            
        except Exception as e:
            logger.error(f"Error fixing dependencies: {e}")
    
    def _update_migration_status(self, stats: Dict[str, Any]) -> None:
        """Update project context with intelligent migration status"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            migration_record = {
                "intelligent_migration_completed": True,
                "migration_timestamp": datetime.datetime.now().isoformat(),
                "total_tasks_analyzed": stats.get('total_tasks', 0),
                "phases_created": stats.get('phases_created', 0),
                "migration_method": "ai_powered_multi_phase_analysis",
                "domain_analysis": stats.get('domain_analysis', {}),
                "phase_structure": {
                    "recommended_phases": len(stats.get('phase_structure', {}).get('recommended_phases', [])),
                    "reasoning": stats.get('phase_structure', {}).get('reasoning', [])
                },
                "phase_system_version": "2.0"
            }
            
            cursor.execute("""
                INSERT OR REPLACE INTO project_context (context_key, value, last_updated, updated_by, description)
                VALUES (?, ?, ?, ?, ?)
            """, (
                "agent_mcp_intelligent_migration",
                json.dumps(migration_record),
                datetime.datetime.now().isoformat(),
                "intelligent_migration",
                "AI-powered intelligent multi-phase migration with dependency optimization"
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating intelligent migration status: {e}")


async def run_intelligent_migration() -> bool:
    """
    Entry point for intelligent multi-phase migration.
    This should be called during Agent MCP initialization.
    """
    migration_manager = IntelligentMigrationManager()
    return await migration_manager.run_intelligent_migration()