#!/usr/bin/env python3
"""
Hierarchical Task Migration System for Agent MCP

This system handles the complete task hierarchy, not just root tasks.
It migrates entire task trees to phases while preserving internal structure.
"""

import json
import sqlite3
import datetime
from typing import Dict, List, Any, Optional, Set
from .config import logger
from ..db.connection import get_db_connection


class TaskHierarchyAnalyzer:
    """Analyzes and maps the complete task hierarchy"""
    
    def __init__(self):
        self.tasks_map: Dict[str, Dict[str, Any]] = {}
        self.root_tasks: List[str] = []
        self.task_trees: Dict[str, Dict[str, Any]] = {}
    
    def load_all_tasks(self) -> None:
        """Load all tasks from database and build hierarchy map"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM tasks ORDER BY created_at")
            all_tasks = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            # Build tasks map
            for task in all_tasks:
                task_id = task['task_id']
                self.tasks_map[task_id] = task
                
                # Identify root tasks
                if task.get('parent_task') is None:
                    self.root_tasks.append(task_id)
            
            logger.info(f"📊 Loaded {len(all_tasks)} total tasks: {len(self.root_tasks)} root tasks, {len(all_tasks) - len(self.root_tasks)} subtasks")
            
        except Exception as e:
            logger.error(f"Error loading task hierarchy: {e}")
    
    def build_task_tree(self, root_task_id: str) -> Dict[str, Any]:
        """Build complete task tree starting from a root task"""
        if root_task_id not in self.tasks_map:
            return {}
        
        root_task = self.tasks_map[root_task_id]
        
        # Find all children recursively
        children = self.get_all_descendants(root_task_id)
        
        task_tree = {
            'root_task': root_task,
            'all_tasks': [root_task] + children,
            'total_count': 1 + len(children),
            'status_distribution': {},
            'depth_levels': {}
        }
        
        # Analyze task tree
        for task in task_tree['all_tasks']:
            status = task.get('status', 'unknown')
            task_tree['status_distribution'][status] = task_tree['status_distribution'].get(status, 0) + 1
        
        return task_tree
    
    def get_all_descendants(self, parent_task_id: str) -> List[Dict[str, Any]]:
        """Get all descendant tasks recursively"""
        descendants = []
        
        # Find direct children
        direct_children = [
            task for task in self.tasks_map.values() 
            if task.get('parent_task') == parent_task_id
        ]
        
        for child in direct_children:
            descendants.append(child)
            # Recursively get grandchildren
            grandchildren = self.get_all_descendants(child['task_id'])
            descendants.extend(grandchildren)
        
        return descendants
    
    def analyze_complete_hierarchy(self) -> Dict[str, Any]:
        """Analyze the complete task hierarchy"""
        self.load_all_tasks()
        
        analysis = {
            'total_tasks': len(self.tasks_map),
            'root_tasks_count': len(self.root_tasks),
            'subtasks_count': len(self.tasks_map) - len(self.root_tasks),
            'task_trees': {},
            'migration_plan': []
        }
        
        # Build task trees for each root task
        for root_id in self.root_tasks:
            tree = self.build_task_tree(root_id)
            analysis['task_trees'][root_id] = tree
            
            # Create migration plan entry
            analysis['migration_plan'].append({
                'root_task_id': root_id,
                'root_task_title': tree['root_task']['title'],
                'tree_size': tree['total_count'],
                'status_distribution': tree['status_distribution']
            })
        
        return analysis


class HierarchicalMigrationManager:
    """Manages hierarchical migration of complete task trees to phases"""
    
    def __init__(self):
        self.analyzer = TaskHierarchyAnalyzer()
    
    def needs_hierarchical_migration(self) -> bool:
        """Check if hierarchical migration is needed"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if phases exist
            cursor.execute("SELECT COUNT(*) as count FROM tasks WHERE task_id LIKE 'phase_%'")
            phase_count = cursor.fetchone()['count']
            
            # Check total task count
            cursor.execute("SELECT COUNT(*) as count FROM tasks")
            total_tasks = cursor.fetchone()['count']
            
            conn.close()
            
            needs_migration = phase_count == 0 and total_tasks > 0
            
            if needs_migration:
                logger.info(f"🔄 Hierarchical migration needed: {total_tasks} tasks without phase system")
            else:
                logger.info("✅ Phase system already active or no tasks to migrate")
            
            return needs_migration
            
        except Exception as e:
            logger.error(f"Error checking hierarchical migration status: {e}")
            return False
    
    def create_foundation_phase(self, total_tasks: int) -> bool:
        """Create Foundation phase for all migrated tasks"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if Foundation phase already exists
            cursor.execute("SELECT task_id FROM tasks WHERE task_id = 'phase_1_foundation'")
            if cursor.fetchone():
                logger.info("Foundation phase already exists")
                conn.close()
                return True
            
            created_at = datetime.datetime.now().isoformat()
            
            initial_notes = [{
                "timestamp": created_at,
                "author": "hierarchical_migration",
                "content": f"🚀 Hierarchical migration: Foundation phase created for {total_tasks} tasks (including complete task trees). All task hierarchies preserved within Foundation. Complete all tasks before advancing to Phase 2: Intelligence."
            }]
            
            phase_data = {
                "task_id": "phase_1_foundation",
                "title": "Phase 1: Foundation",
                "description": "Core system architecture, database, authentication, and basic APIs\n\n🧠 Theory Focus: System foundation and core data structures\n\n📊 Migrated: All existing task hierarchies preserved within this phase",
                "assigned_to": None,
                "created_by": "hierarchical_migration",
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
            
            conn.commit()
            conn.close()
            
            logger.info("✅ Created Foundation phase for hierarchical migration")
            return True
            
        except Exception as e:
            logger.error(f"Error creating Foundation phase: {e}")
            return False
    
    def migrate_task_tree(self, root_task_id: str, task_tree: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate a complete task tree to Foundation phase"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            migrated_count = 0
            failed_count = 0
            migration_details = []
            
            # Migration strategy:
            # 1. Root task becomes child of Foundation phase
            # 2. All subtasks keep their existing parent relationships
            # 3. Internal hierarchy is preserved within the phase
            
            updated_at = datetime.datetime.now().isoformat()
            
            # Migrate root task to Foundation phase
            root_task = task_tree['root_task']
            
            try:
                # Add migration note to root task
                current_notes = json.loads(root_task.get('notes', '[]'))
                migration_note = {
                    "timestamp": updated_at,
                    "author": "hierarchical_migration",
                    "content": f"🚀 Hierarchical migration: Task tree migrated to Foundation phase. This task and its {task_tree['total_count'] - 1} subtasks now follow linear phase progression. Complete entire task tree before advancing phases."
                }
                current_notes.append(migration_note)
                
                # Update root task to be child of Foundation phase
                cursor.execute("""
                    UPDATE tasks 
                    SET parent_task = 'phase_1_foundation', updated_at = ?, notes = ?
                    WHERE task_id = ?
                """, (updated_at, json.dumps(current_notes), root_task_id))
                
                migrated_count += 1
                migration_details.append({
                    'task_id': root_task_id,
                    'title': root_task['title'],
                    'role': 'root_task',
                    'new_parent': 'phase_1_foundation'
                })
                
                logger.info(f"📦 Migrated root task: {root_task['title'][:50]}...")
                
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to migrate root task {root_task_id}: {e}")
            
            # Add migration notes to all subtasks (they keep existing parent relationships)
            for task in task_tree['all_tasks'][1:]:  # Skip root task (already handled)
                try:
                    task_id = task['task_id']
                    current_notes = json.loads(task.get('notes', '[]'))
                    
                    migration_note = {
                        "timestamp": updated_at,
                        "author": "hierarchical_migration",
                        "content": f"🔗 Hierarchical migration: Task hierarchy preserved within Foundation phase. Parent-child relationships maintained. Complete this task as part of Foundation phase progression."
                    }
                    current_notes.append(migration_note)
                    
                    # Update subtask with migration note (parent_task stays the same)
                    cursor.execute("""
                        UPDATE tasks 
                        SET updated_at = ?, notes = ?
                        WHERE task_id = ?
                    """, (updated_at, json.dumps(current_notes), task_id))
                    
                    migrated_count += 1
                    migration_details.append({
                        'task_id': task_id,
                        'title': task['title'],
                        'role': 'subtask',
                        'parent_preserved': task.get('parent_task')
                    })
                    
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Failed to add migration note to subtask {task.get('task_id', 'unknown')}: {e}")
            
            conn.commit()
            conn.close()
            
            return {
                'migrated_count': migrated_count,
                'failed_count': failed_count,
                'tree_size': task_tree['total_count'],
                'migration_details': migration_details
            }
            
        except Exception as e:
            logger.error(f"Error migrating task tree {root_task_id}: {e}")
            return {'migrated_count': 0, 'failed_count': task_tree['total_count'], 'tree_size': task_tree['total_count']}
    
    def run_hierarchical_migration(self) -> bool:
        """Run the complete hierarchical migration process"""
        try:
            logger.info("🚀 Starting hierarchical task tree migration...")
            
            # Step 1: Check if migration is needed
            if not self.needs_hierarchical_migration():
                return True
            
            # Step 2: Analyze complete task hierarchy
            logger.info("📊 Analyzing complete task hierarchy...")
            analysis = self.analyzer.analyze_complete_hierarchy()
            
            total_tasks = analysis['total_tasks']
            root_count = analysis['root_tasks_count']
            subtask_count = analysis['subtasks_count']
            
            logger.info(f"📋 Hierarchy analysis: {total_tasks} total tasks ({root_count} root, {subtask_count} subtasks)")
            
            # Step 3: Create Foundation phase
            logger.info("📊 Creating Foundation phase for hierarchical migration...")
            if not self.create_foundation_phase(total_tasks):
                logger.error("Failed to create Foundation phase")
                return False
            
            # Step 4: Migrate each task tree
            logger.info("🔄 Migrating complete task trees...")
            total_migrated = 0
            total_failed = 0
            
            for plan in analysis['migration_plan']:
                root_id = plan['root_task_id']
                tree_size = plan['tree_size']
                
                logger.info(f"📦 Migrating task tree: {plan['root_task_title'][:50]}... ({tree_size} tasks)")
                
                task_tree = analysis['task_trees'][root_id]
                migration_result = self.migrate_task_tree(root_id, task_tree)
                
                total_migrated += migration_result['migrated_count']
                total_failed += migration_result['failed_count']
                
                logger.info(f"   ✅ Migrated {migration_result['migrated_count']}/{tree_size} tasks")
            
            # Step 5: Update project context
            self.update_migration_status({
                'total_tasks': total_tasks,
                'migrated_tasks': total_migrated,
                'failed_tasks': total_failed,
                'root_trees': len(analysis['migration_plan'])
            })
            
            # Final summary
            logger.info(f"✅ Hierarchical migration completed!")
            logger.info(f"   📊 Total tasks: {total_tasks}")
            logger.info(f"   ✅ Migrated: {total_migrated}")
            logger.info(f"   ❌ Failed: {total_failed}")
            logger.info(f"   🌳 Task trees: {len(analysis['migration_plan'])}")
            logger.info("🎯 Complete task hierarchy now organized under Foundation phase")
            
            return total_failed == 0
            
        except Exception as e:
            logger.error(f"Critical error during hierarchical migration: {e}")
            return False
    
    def update_migration_status(self, stats: Dict[str, Any]) -> None:
        """Update project context with hierarchical migration status"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            migration_record = {
                "hierarchical_migration_completed": True,
                "migration_timestamp": datetime.datetime.now().isoformat(),
                "total_tasks_migrated": stats.get('total_tasks', 0),
                "failed_tasks": stats.get('failed_tasks', 0),
                "task_trees_migrated": stats.get('root_trees', 0),
                "migration_method": "hierarchical_task_tree_preservation",
                "phase_system_version": "1.0",
                "hierarchy_preserved": True
            }
            
            cursor.execute("""
                INSERT OR REPLACE INTO project_context (context_key, value, last_updated, updated_by, description)
                VALUES (?, ?, ?, ?, ?)
            """, (
                "agent_mcp_hierarchical_migration",
                json.dumps(migration_record),
                datetime.datetime.now().isoformat(),
                "hierarchical_migration",
                "Complete hierarchical task tree migration to phase system status"
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating hierarchical migration status: {e}")


def run_hierarchical_migration() -> bool:
    """
    Entry point for hierarchical task tree migration.
    This should be called during Agent MCP initialization.
    """
    migration_manager = HierarchicalMigrationManager()
    return migration_manager.run_hierarchical_migration()