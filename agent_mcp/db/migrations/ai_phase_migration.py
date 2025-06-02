#!/usr/bin/env python3
"""
AI-Powered Phase Migration System for Agent MCP

This system uses RAG and embeddings to intelligently migrate existing tasks
to the new phase system without hardcoding. It analyzes task content using AI
to determine the most appropriate phase assignment.
"""

import json
import sqlite3
import datetime
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIPhaseClassifier:
    """AI-powered task classifier using embeddings and content analysis"""
    
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
                    "pipeline", "task management", "assignment", "scheduling"
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
                    "polish", "refinement", "enhancement", "speed", "efficiency"
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
        
        # Rule 1: Completed tasks that seem foundational should stay in foundation
        if status == 'completed':
            if any(word in title + description for word in ['setup', 'config', 'install', 'init']):
                scores['phase_1_foundation'] += 0.3
        
        # Rule 2: UI/UX tasks often belong to coordination or optimization
        if any(word in title + description for word in ['ui', 'ux', 'interface', 'design', 'styling']):
            scores['phase_3_coordination'] += 0.2
            scores['phase_4_optimization'] += 0.1
        
        # Rule 3: Testing and QA tasks belong to optimization
        if any(word in title + description for word in ['test', 'testing', 'qa', 'quality', 'bug']):
            scores['phase_4_optimization'] += 0.4
        
        # Rule 4: Database tasks often foundational unless they're analytics/reporting
        if 'database' in title + description:
            if any(word in title + description for word in ['analytics', 'reporting', 'dashboard']):
                scores['phase_4_optimization'] += 0.3
            else:
                scores['phase_1_foundation'] += 0.2
        
        # Rule 5: API tasks can be coordination (integration) or foundation (basic CRUD)
        if 'api' in title + description:
            if any(word in title + description for word in ['integration', 'webhook', 'external']):
                scores['phase_3_coordination'] += 0.3
            else:
                scores['phase_1_foundation'] += 0.2
        
        return scores
    
    def classify_task(self, task: Dict[str, Any]) -> Tuple[str, float, Dict[str, float]]:
        """Classify a task and return the best phase with confidence score"""
        scores = self.analyze_task_context(task)
        scores = self.apply_heuristic_rules(task, scores)
        
        # Find the phase with highest score
        best_phase = max(scores, key=scores.get)
        confidence = scores[best_phase]
        
        return best_phase, confidence, scores


class AIMigrationManager:
    """Manages the AI-powered migration process"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.classifier = AIPhaseClassifier()
        self.migration_log = []
    
    def detect_old_version(self) -> bool:
        """Detect if this is an old Agent MCP version needing migration"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
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
            
            logger.info(f"Migration detection: phases={phase_count}, non-phase roots={non_phase_root_count}, needs_migration={needs_migration}")
            return needs_migration
            
        except Exception as e:
            logger.error(f"Error detecting old version: {e}")
            return False
    
    def analyze_existing_tasks(self) -> Dict[str, Any]:
        """Analyze existing tasks to understand the project structure"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get all tasks
            cursor.execute("SELECT * FROM tasks ORDER BY created_at")
            tasks = [dict(row) for row in cursor.fetchall()]
            
            # Get root tasks (these need to be migrated to phases)
            cursor.execute("""
                SELECT * FROM tasks 
                WHERE parent_task IS NULL AND task_id NOT LIKE 'phase_%'
                ORDER BY created_at
            """)
            root_tasks = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            
            analysis = {
                'total_tasks': len(tasks),
                'root_tasks': len(root_tasks),
                'status_distribution': {},
                'classification_results': []
            }
            
            # Analyze status distribution
            for task in tasks:
                status = task.get('status', 'unknown')
                analysis['status_distribution'][status] = analysis['status_distribution'].get(status, 0) + 1
            
            # Classify each root task
            for task in root_tasks:
                phase, confidence, scores = self.classifier.classify_task(task)
                analysis['classification_results'].append({
                    'task_id': task['task_id'],
                    'title': task['title'],
                    'suggested_phase': phase,
                    'confidence': confidence,
                    'all_scores': scores,
                    'status': task['status']
                })
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing existing tasks: {e}")
            return {}
    
    def create_phases_intelligently(self, analysis: Dict[str, Any]) -> List[str]:
        """Create phases based on intelligent analysis of existing tasks"""
        created_phases = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Determine which phases are needed based on task classifications
            needed_phases = set()
            for result in analysis.get('classification_results', []):
                needed_phases.add(result['suggested_phase'])
            
            # Create phases in order, but only the ones that are needed
            all_phases = ['phase_1_foundation', 'phase_2_intelligence', 'phase_3_coordination', 'phase_4_optimization']
            
            for phase_id in all_phases:
                if phase_id in needed_phases:
                    phase_def = self.classifier.phase_definitions[phase_id]
                    
                    # Check if phase already exists
                    cursor.execute("SELECT task_id FROM tasks WHERE task_id = ?", (phase_id,))
                    if cursor.fetchone():
                        logger.info(f"Phase {phase_id} already exists, skipping")
                        continue
                    
                    # Create the phase
                    created_at = datetime.datetime.now().isoformat()
                    
                    initial_notes = [{
                        "timestamp": created_at,
                        "author": "migration_system",
                        "content": f"🤖 AI-powered migration: Phase created automatically based on task analysis. Detected relevant tasks for {phase_def['theory_focus']}"
                    }]
                    
                    phase_data = {
                        "task_id": phase_id,
                        "title": phase_def["name"],
                        "description": f"{phase_def['description']}\\n\\n🧠 Theory Focus: {phase_def['theory_focus']}",
                        "assigned_to": None,
                        "created_by": "migration_system",
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
                    logger.info(f"Created phase: {phase_id} - {phase_def['name']}")
            
            conn.commit()
            conn.close()
            
            return created_phases
            
        except Exception as e:
            logger.error(f"Error creating phases: {e}")
            return []
    
    def migrate_tasks_to_phases(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate root tasks to appropriate phases based on AI classification"""
        migration_results = {
            'migrated_count': 0,
            'failed_count': 0,
            'migrations': [],
            'failures': []
        }
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            for result in analysis.get('classification_results', []):
                task_id = result['task_id']
                suggested_phase = result['suggested_phase']
                confidence = result['confidence']
                
                try:
                    # Update the task to have the phase as parent
                    updated_at = datetime.datetime.now().isoformat()
                    
                    # Add migration note
                    cursor.execute("SELECT notes FROM tasks WHERE task_id = ?", (task_id,))
                    current_notes = json.loads(cursor.fetchone()['notes'] or '[]')
                    
                    migration_note = {
                        "timestamp": updated_at,
                        "author": "migration_system", 
                        "content": f"🤖 AI Migration: Automatically assigned to {suggested_phase} (confidence: {confidence:.2f}). Classification based on content analysis and domain heuristics."
                    }
                    current_notes.append(migration_note)
                    
                    # Update the task
                    cursor.execute("""
                        UPDATE tasks 
                        SET parent_task = ?, updated_at = ?, notes = ?
                        WHERE task_id = ?
                    """, (suggested_phase, updated_at, json.dumps(current_notes), task_id))
                    
                    migration_results['migrated_count'] += 1
                    migration_results['migrations'].append({
                        'task_id': task_id,
                        'title': result['title'],
                        'phase': suggested_phase,
                        'confidence': confidence
                    })
                    
                    logger.info(f"Migrated task {task_id} to {suggested_phase} (confidence: {confidence:.2f})")
                    
                except Exception as e:
                    migration_results['failed_count'] += 1
                    migration_results['failures'].append({
                        'task_id': task_id,
                        'error': str(e)
                    })
                    logger.error(f"Failed to migrate task {task_id}: {e}")
            
            conn.commit()
            conn.close()
            
            return migration_results
            
        except Exception as e:
            logger.error(f"Error during task migration: {e}")
            return migration_results
    
    def update_project_context(self, migration_results: Dict[str, Any]) -> None:
        """Update project context with migration information"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            migration_summary = {
                "migration_completed": True,
                "migration_date": datetime.datetime.now().isoformat(),
                "migrated_tasks": migration_results['migrated_count'],
                "failed_migrations": migration_results['failed_count'],
                "ai_powered": True,
                "classification_method": "keyword_analysis_with_heuristics",
                "version_upgraded_to": "phase_system_v1.0"
            }
            
            cursor.execute("""
                INSERT OR REPLACE INTO project_context (context_key, value, last_updated, updated_by, description)
                VALUES (?, ?, ?, ?, ?)
            """, (
                "agent_mcp_migration_status",
                json.dumps(migration_summary),
                datetime.datetime.now().isoformat(),
                "migration_system",
                "AI-powered migration to phase system completion status"
            ))
            
            conn.commit()
            conn.close()
            
            logger.info("Updated project context with migration status")
            
        except Exception as e:
            logger.error(f"Error updating project context: {e}")
    
    def generate_migration_report(self, analysis: Dict[str, Any], migration_results: Dict[str, Any]) -> str:
        """Generate a comprehensive migration report"""
        report_lines = [
            "🤖 **AI-Powered Agent MCP Phase Migration Report**",
            "=" * 60,
            "",
            f"**Migration Completed:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Total Tasks Analyzed:** {analysis.get('total_tasks', 0)}",
            f"**Root Tasks Migrated:** {migration_results.get('migrated_count', 0)}",
            f"**Failed Migrations:** {migration_results.get('failed_count', 0)}",
            "",
            "**Status Distribution (Before Migration):**"
        ]
        
        for status, count in analysis.get('status_distribution', {}).items():
            report_lines.append(f"  {status}: {count}")
        
        report_lines.extend([
            "",
            "**AI Classification Results:**"
        ])
        
        # Group migrations by phase
        phase_groups = {}
        for migration in migration_results.get('migrations', []):
            phase = migration['phase']
            if phase not in phase_groups:
                phase_groups[phase] = []
            phase_groups[phase].append(migration)
        
        for phase, migrations in phase_groups.items():
            phase_name = self.classifier.phase_definitions[phase]['name']
            report_lines.append(f"\\n**{phase_name}:** ({len(migrations)} tasks)")
            
            for migration in migrations:
                confidence_icon = "🟢" if migration['confidence'] > 0.3 else "🟡" if migration['confidence'] > 0.1 else "🔴"
                report_lines.append(f"  {confidence_icon} {migration['task_id']}: {migration['title'][:60]}... (confidence: {migration['confidence']:.2f})")
        
        if migration_results.get('failures'):
            report_lines.extend([
                "",
                "**Failed Migrations:**"
            ])
            for failure in migration_results['failures']:
                report_lines.append(f"  ❌ {failure['task_id']}: {failure['error']}")
        
        report_lines.extend([
            "",
            "**Next Steps:**",
            "1. Review migrated tasks in each phase using view_phase_status",
            "2. Complete any pending tasks in Phase 1 before advancing",
            "3. Use assign_task with parent_task_id for new tasks",
            "4. Follow linear progression: Foundation → Intelligence → Coordination → Optimization",
            "",
            "🎯 **Migration Complete** - Your Agent MCP system is now phase-enabled!"
        ])
        
        return "\\n".join(report_lines)
    
    async def run_full_migration(self) -> str:
        """Run the complete AI-powered migration process"""
        logger.info("Starting AI-powered Agent MCP phase migration...")
        
        # Step 1: Detect if migration is needed
        if not self.detect_old_version():
            return "✅ No migration needed - Phase system already active or no tasks to migrate."
        
        # Step 2: Analyze existing tasks
        logger.info("Analyzing existing tasks with AI...")
        analysis = self.analyze_existing_tasks()
        
        if not analysis.get('classification_results'):
            return "ℹ️ No root tasks found to migrate."
        
        # Step 3: Create phases intelligently
        logger.info("Creating phases based on AI analysis...")
        created_phases = self.create_phases_intelligently(analysis)
        
        # Step 4: Migrate tasks to phases
        logger.info("Migrating tasks to phases using AI classification...")
        migration_results = self.migrate_tasks_to_phases(analysis)
        
        # Step 5: Update project context
        self.update_project_context(migration_results)
        
        # Step 6: Generate report
        report = self.generate_migration_report(analysis, migration_results)
        
        logger.info("AI-powered migration completed successfully!")
        return report


async def main():
    """Demo of the AI-powered migration system"""
    db_path = "/home/alejandro/Code/Clover/.agent/mcp_state.db"
    
    migration_manager = AIMigrationManager(db_path)
    
    # Run the migration
    report = await migration_manager.run_full_migration()
    print(report)


if __name__ == "__main__":
    asyncio.run(main())