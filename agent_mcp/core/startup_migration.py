#!/usr/bin/env python3
"""
Automatic Startup Migration System for Agent MCP

This system runs automatically on Agent MCP startup to detect old versions
and seamlessly migrate them to the new phase system using AI-powered classification.
"""

import json
import sqlite3
import datetime
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from .config import logger
from ..db.connection import get_db_connection


class AIPhaseClassifier:
    """AI-powered task classifier using content analysis and domain heuristics"""
    
    def __init__(self):
        self.phase_definitions = {
            "phase_1_foundation": {
                "name": "Phase 1: Foundation",
                "description": "Core system architecture, database, authentication, and basic APIs",
                "keywords": [
                    "database", "schema", "authentication", "auth", "login", "setup", 
                    "architecture", "config", "configuration", "install", "deployment",
                    "infrastructure", "basic", "core", "fundamental", "init", "initialize",
                    "bootstrap", "foundation", "structure", "framework", "base", "system"
                ],
                "theory_focus": "System foundation and core data structures"
            },
            "phase_2_intelligence": {
                "name": "Phase 2: Intelligence", 
                "description": "RAG system, embeddings, context management, and AI integration",
                "keywords": [
                    "ai", "artificial intelligence", "embeddings", "vector", "rag", 
                    "retrieval", "search", "semantic", "nlp", "context", "smart",
                    "intelligence", "learning", "recommendation", "analysis", "chatbot",
                    "llm", "gpt", "openai", "machine learning", "knowledge", "understanding"
                ],
                "theory_focus": "Knowledge systems and AI intelligence integration"
            },
            "phase_3_coordination": {
                "name": "Phase 3: Coordination",
                "description": "Multi-agent workflows, task orchestration, and system integration", 
                "keywords": [
                    "workflow", "orchestration", "integration", "coordination", "agent",
                    "multi-agent", "collaboration", "sync", "communication", "api",
                    "webhook", "event", "notification", "automation", "process",
                    "pipeline", "task management", "assignment", "scheduling", "ui", "ux",
                    "interface", "frontend", "user experience", "design", "styling"
                ],
                "theory_focus": "Agent coordination and workflow orchestration"
            },
            "phase_4_optimization": {
                "name": "Phase 4: Optimization",
                "description": "Performance tuning, scaling, monitoring, and production readiness",
                "keywords": [
                    "performance", "optimization", "scaling", "monitoring", "production",
                    "deployment", "ci/cd", "testing", "quality", "security", "audit",
                    "analytics", "metrics", "dashboard", "reporting", "maintenance",
                    "polish", "refinement", "enhancement", "speed", "efficiency", "test",
                    "bug", "fix", "optimize", "improve"
                ],
                "theory_focus": "System optimization and production deployment"
            }
        }
    
    def calculate_keyword_score(self, text: str, keywords: List[str]) -> float:
        """Calculate keyword match score for a text"""
        text_lower = text.lower()
        matches = sum(1 for keyword in keywords if keyword in text_lower)
        return matches / len(keywords) if keywords else 0
    
    def analyze_task_context(self, task: Dict[str, Any]) -> Dict[str, float]:
        """Analyze task content and return phase scores"""
        # Combine title, description, and any notes for analysis
        full_text = f"{task.get('title', '')} {task.get('description', '')}"
        
        # Add notes if they exist
        notes = task.get('notes', '[]')
        if isinstance(notes, str):
            try:
                notes_list = json.loads(notes)
                notes_text = " ".join([note.get('content', '') for note in notes_list])
                full_text += f" {notes_text}"
            except json.JSONDecodeError:
                pass
        
        scores = {}
        for phase_id, phase_def in self.phase_definitions.items():
            scores[phase_id] = self.calculate_keyword_score(full_text, phase_def['keywords'])
        
        return scores
    
    def apply_heuristic_rules(self, task: Dict[str, Any], scores: Dict[str, float]) -> Dict[str, float]:
        """Apply domain-specific heuristic rules to adjust scores"""
        title = task.get('title', '').lower()
        description = task.get('description', '').lower()
        status = task.get('status', '')
        
        # Rule 1: Completed foundational tasks should stay in foundation
        if status == 'completed':
            if any(word in title + description for word in ['setup', 'config', 'install', 'init', 'create']):
                scores['phase_1_foundation'] += 0.4
        
        # Rule 2: UI/UX and marketing tasks often belong to coordination
        if any(word in title + description for word in ['ui', 'ux', 'interface', 'design', 'styling', 'page', 'component', 'marketing', 'home', 'website']):
            scores['phase_3_coordination'] += 0.3
        
        # Rule 3: Testing, QA, and polish tasks belong to optimization
        if any(word in title + description for word in ['test', 'testing', 'qa', 'quality', 'bug', 'fix', 'polish', 'enhance', 'improve']):
            scores['phase_4_optimization'] += 0.4
        
        # Rule 4: Calculator and complex features are coordination
        if any(word in title + description for word in ['calculator', 'quote', 'pricing', 'form', 'feature']):
            scores['phase_3_coordination'] += 0.3
        
        # Rule 5: Database and core setup is foundation
        if any(word in title + description for word in ['database', 'schema', 'table', 'migration', 'auth', 'authentication']):
            scores['phase_1_foundation'] += 0.3
        
        return scores
    
    def classify_task(self, task: Dict[str, Any]) -> Tuple[str, float, Dict[str, float]]:
        """Classify a task and return the best phase with confidence score"""
        scores = self.analyze_task_context(task)
        scores = self.apply_heuristic_rules(task, scores)
        
        # Find the phase with highest score
        best_phase = max(scores, key=scores.get)
        confidence = scores[best_phase]
        
        # If confidence is very low, default to foundation
        if confidence < 0.05:
            best_phase = 'phase_1_foundation'
            confidence = 0.1
        
        return best_phase, confidence, scores


class StartupMigrationManager:
    """Manages automatic startup migration to phase system"""
    
    def __init__(self):
        self.classifier = AIPhaseClassifier()
    
    def needs_migration(self) -> bool:
        """Check if migration is needed (old version without phases)"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if phases already exist
            cursor.execute("SELECT COUNT(*) as count FROM tasks WHERE task_id LIKE 'phase_%'")
            phase_count = cursor.fetchone()['count']
            
            # Check if there are root tasks that aren't phases
            cursor.execute("""
                SELECT COUNT(*) as count FROM tasks 
                WHERE parent_task IS NULL AND task_id NOT LIKE 'phase_%'
            """)
            non_phase_root_count = cursor.fetchone()['count']
            
            conn.close()
            
            # Need migration if no phases exist but there are non-phase root tasks
            needs_migration = phase_count == 0 and non_phase_root_count > 0
            
            if needs_migration:
                logger.info(f"🔄 Startup Migration: Detected {non_phase_root_count} root tasks needing migration to phase system")
            else:
                logger.info("✅ Phase system already active or no migration needed")
            
            return needs_migration
            
        except Exception as e:
            logger.error(f"Error checking migration status: {e}")
            return False
    
    def analyze_and_classify_tasks(self) -> List[Dict[str, Any]]:
        """Analyze existing root tasks and classify them using AI"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get root tasks that need migration
            cursor.execute("""
                SELECT * FROM tasks 
                WHERE parent_task IS NULL AND task_id NOT LIKE 'phase_%'
                ORDER BY created_at
            """)
            root_tasks = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            
            classifications = []
            for task in root_tasks:
                phase, confidence, scores = self.classifier.classify_task(task)
                classifications.append({
                    'task': task,
                    'suggested_phase': phase,
                    'confidence': confidence,
                    'all_scores': scores
                })
            
            logger.info(f"🤖 AI Classification: Analyzed {len(classifications)} root tasks")
            return classifications
            
        except Exception as e:
            logger.error(f"Error analyzing tasks: {e}")
            return []
    
    def enforce_linear_progression(self, classifications: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enforce linear phase progression - all tasks must start from Phase 1"""
        logger.info("🔄 Enforcing linear phase progression for migration...")
        
        # For migration, we need to ensure linear progression
        # All existing tasks should be placed in the earliest phase (Foundation)
        # Users can then properly progress through phases as they complete work
        
        adjusted_classifications = []
        for classification in classifications:
            task = classification['task']
            original_phase = classification['suggested_phase']
            
            # For startup migration, place all tasks in Foundation phase
            # This ensures proper linear progression from the beginning
            adjusted_classification = classification.copy()
            adjusted_classification['suggested_phase'] = 'phase_1_foundation'
            adjusted_classification['original_ai_suggestion'] = original_phase
            adjusted_classification['migration_reason'] = 'linear_progression_enforcement'
            
            adjusted_classifications.append(adjusted_classification)
            
            logger.info(f"📦 Task '{task['title'][:50]}...' → Phase 1: Foundation (was suggested: {original_phase})")
        
        logger.info("✅ All tasks assigned to Foundation phase for proper linear progression")
        return adjusted_classifications

    def create_needed_phases(self, classifications: List[Dict[str, Any]]) -> List[str]:
        """Create only the phases that are needed based on linear progression"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # For startup migration, we always start with Foundation phase
            # Users will create subsequent phases as they complete previous ones
            needed_phases = {'phase_1_foundation'}
            
            created_phases = []
            all_phases = ['phase_1_foundation', 'phase_2_intelligence', 'phase_3_coordination', 'phase_4_optimization']
            
            for phase_id in all_phases:
                if phase_id in needed_phases:
                    phase_def = self.classifier.phase_definitions[phase_id]
                    
                    # Check if phase already exists
                    cursor.execute("SELECT task_id FROM tasks WHERE task_id = ?", (phase_id,))
                    if cursor.fetchone():
                        continue
                    
                    # Create the phase
                    created_at = datetime.datetime.now().isoformat()
                    
                    # Count tasks being migrated to this phase
                    task_count = sum(1 for c in classifications if c['suggested_phase'] == phase_id)
                    
                    if phase_id == 'phase_1_foundation':
                        initial_notes = [{
                            "timestamp": created_at,
                            "author": "startup_migration",
                            "content": f"🚀 Linear progression migration: Foundation phase created for {task_count} existing tasks. All tasks start here to ensure proper phase sequence. Complete these tasks before advancing to Phase 2: Intelligence."
                        }]
                    else:
                        initial_notes = [{
                            "timestamp": created_at,
                            "author": "startup_migration",
                            "content": f"🚀 Automatic startup migration: Phase created for {task_count} existing tasks. AI-powered classification based on content analysis."
                        }]
                    
                    phase_data = {
                        "task_id": phase_id,
                        "title": phase_def["name"],
                        "description": f"{phase_def['description']}\n\n🧠 Theory Focus: {phase_def['theory_focus']}",
                        "assigned_to": None,
                        "created_by": "startup_migration",
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
                    
                    created_phases.append(phase_id)
                    logger.info(f"📊 Created phase: {phase_def['name']} for {task_count} tasks")
            
            conn.commit()
            conn.close()
            
            return created_phases
            
        except Exception as e:
            logger.error(f"Error creating phases: {e}")
            return []
    
    def migrate_tasks(self, classifications: List[Dict[str, Any]]) -> Dict[str, int]:
        """Migrate tasks to their classified phases"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            migration_stats = {'migrated': 0, 'failed': 0}
            
            for classification in classifications:
                task = classification['task']
                phase = classification['suggested_phase']
                original_suggestion = classification.get('original_ai_suggestion', phase)
                migration_reason = classification.get('migration_reason', 'ai_classification')
                
                try:
                    task_id = task['task_id']
                    updated_at = datetime.datetime.now().isoformat()
                    
                    # Add migration note with linear progression explanation
                    current_notes = json.loads(task.get('notes', '[]'))
                    
                    if migration_reason == 'linear_progression_enforcement':
                        migration_note = {
                            "timestamp": updated_at,
                            "author": "startup_migration",
                            "content": f"🚀 Linear progression migration: Assigned to {phase} to ensure proper phase sequence. AI suggested {original_suggestion}, but linear progression requires starting from Foundation. Complete this phase before advancing to subsequent phases."
                        }
                    else:
                        migration_note = {
                            "timestamp": updated_at,
                            "author": "startup_migration",
                            "content": f"🤖 Automatic migration: Assigned to {phase}. Task now follows linear phase progression."
                        }
                    
                    current_notes.append(migration_note)
                    
                    # Update the task
                    cursor.execute("""
                        UPDATE tasks 
                        SET parent_task = ?, updated_at = ?, notes = ?
                        WHERE task_id = ?
                    """, (phase, updated_at, json.dumps(current_notes), task_id))
                    
                    migration_stats['migrated'] += 1
                    logger.info(f"📦 Migrated: {task['title'][:50]}... → {phase}")
                    
                except Exception as e:
                    migration_stats['failed'] += 1
                    logger.error(f"Failed to migrate task {task.get('task_id', 'unknown')}: {e}")
            
            conn.commit()
            conn.close()
            
            return migration_stats
            
        except Exception as e:
            logger.error(f"Error during task migration: {e}")
            return {'migrated': 0, 'failed': 0}
    
    def update_migration_status(self, stats: Dict[str, Any]) -> None:
        """Update project context with migration completion status"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            migration_record = {
                "startup_migration_completed": True,
                "migration_timestamp": datetime.datetime.now().isoformat(),
                "migrated_tasks": stats.get('migrated', 0),
                "failed_tasks": stats.get('failed', 0),
                "migration_method": "ai_powered_startup_classification",
                "phase_system_version": "1.0"
            }
            
            cursor.execute("""
                INSERT OR REPLACE INTO project_context (context_key, value, last_updated, updated_by, description)
                VALUES (?, ?, ?, ?, ?)
            """, (
                "agent_mcp_phase_migration",
                json.dumps(migration_record),
                datetime.datetime.now().isoformat(),
                "startup_migration",
                "Automatic startup migration to phase system status"
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating migration status: {e}")
    
    def run_startup_migration(self) -> bool:
        """Run the complete automatic startup migration process"""
        try:
            logger.info("🚀 Starting automatic Agent MCP startup migration...")
            
            # Step 1: Check if migration is needed
            if not self.needs_migration():
                return True  # No migration needed, but not an error
            
            # Step 2: Analyze and classify existing tasks
            logger.info("🤖 Analyzing existing tasks with AI classification...")
            classifications = self.analyze_and_classify_tasks()
            
            if not classifications:
                logger.info("ℹ️ No root tasks found to migrate")
                return True
            
            # Step 2.5: Enforce linear progression (all tasks start in Foundation)
            classifications = self.enforce_linear_progression(classifications)
            
            # Step 3: Create needed phases (only Foundation for migration)
            logger.info("📊 Creating Foundation phase for linear progression...")
            created_phases = self.create_needed_phases(classifications)
            
            # Step 4: Migrate tasks to phases
            logger.info("📦 Migrating tasks to appropriate phases...")
            migration_stats = self.migrate_tasks(classifications)
            
            # Step 5: Update migration status
            combined_stats = {
                'migrated': migration_stats['migrated'],
                'failed': migration_stats['failed'],
                'created_phases': len(created_phases)
            }
            self.update_migration_status(combined_stats)
            
            # Log completion
            logger.info(f"✅ Startup migration completed successfully!")
            logger.info(f"   📊 Created {len(created_phases)} phases")
            logger.info(f"   📦 Migrated {migration_stats['migrated']} tasks")
            if migration_stats['failed'] > 0:
                logger.warning(f"   ⚠️ Failed to migrate {migration_stats['failed']} tasks")
            
            logger.info("🎯 Phase system is now active - use assign_task with parent_task_id for new tasks")
            
            return True
            
        except Exception as e:
            logger.error(f"Critical error during startup migration: {e}")
            return False


# Global migration manager instance
_migration_manager = None

def get_migration_manager() -> StartupMigrationManager:
    """Get the global migration manager instance"""
    global _migration_manager
    if _migration_manager is None:
        _migration_manager = StartupMigrationManager()
    return _migration_manager


def run_startup_migration() -> bool:
    """
    Entry point for automatic startup migration.
    This should be called during Agent MCP initialization.
    """
    migration_manager = get_migration_manager()
    return migration_manager.run_startup_migration()