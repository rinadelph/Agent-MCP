#!/usr/bin/env python3
"""
Granular Multi-Step Migration System for Agent MCP

This system breaks down migration into discrete, analyzable steps where each step
can be validated, criticized, and improved before proceeding to the next.
"""

import json
import sqlite3
import datetime
import asyncio
import re
from typing import Dict, List, Any, Optional, Set, Tuple
from .config import logger
from ..db.connection import get_db_connection
from .relationship_aware_migration import RelationshipAwareMigration


class Step1_ProjectStateAnalyzer:
    """Step 1: Understand the current state of the project"""
    
    def __init__(self):
        self.analysis_results = {}
    
    async def analyze_current_state(self, all_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze what has actually been accomplished and what state the project is in"""
        
        logger.info("🔍 Step 1: Analyzing current project state...")
        
        # Basic stats
        total_tasks = len(all_tasks)
        status_counts = {}
        for task in all_tasks:
            status = task.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Calculate completion percentage
        completed = status_counts.get('completed', 0)
        in_progress = status_counts.get('in_progress', 0)
        pending = status_counts.get('pending', 0)
        cancelled = status_counts.get('cancelled', 0)
        
        completion_percentage = (completed / total_tasks * 100) if total_tasks > 0 else 0
        
        # Analyze what's been built (completed tasks)
        completed_tasks = [task for task in all_tasks if task.get('status') == 'completed']
        completed_work_analysis = self._analyze_completed_work(completed_tasks)
        
        # Analyze what's currently being worked on
        active_tasks = [task for task in all_tasks if task.get('status') == 'in_progress']
        current_work_analysis = self._analyze_current_work(active_tasks)
        
        # Analyze what's planned but not started
        pending_tasks = [task for task in all_tasks if task.get('status') == 'pending']
        future_work_analysis = self._analyze_future_work(pending_tasks)
        
        state_analysis = {
            'total_tasks': total_tasks,
            'status_distribution': status_counts,
            'completion_percentage': round(completion_percentage, 1),
            'completed_work': completed_work_analysis,
            'current_work': current_work_analysis,
            'future_work': future_work_analysis,
            'project_maturity': self._assess_project_maturity(completed_work_analysis, current_work_analysis),
            'development_stage': self._identify_development_stage(completed_work_analysis, current_work_analysis)
        }
        
        logger.info(f"   Total tasks: {total_tasks}")
        logger.info(f"   Completion: {completion_percentage:.1f}% ({completed} completed, {in_progress} in progress, {pending} pending)")
        logger.info(f"   Project maturity: {state_analysis['project_maturity']}")
        logger.info(f"   Development stage: {state_analysis['development_stage']}")
        
        return state_analysis
    
    def _analyze_completed_work(self, completed_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze what has actually been built and completed"""
        
        categories = {
            'database_setup': [],
            'authentication': [],
            'basic_apis': [],
            'core_components': [],
            'dashboard_features': [],
            'ui_pages': [],
            'business_logic': [],
            'integrations': [],
            'testing': [],
            'deployment': []
        }
        
        for task in completed_tasks:
            title = task.get('title', '').lower()
            description = task.get('description', '').lower()
            text = f"{title} {description}"
            
            # Categorize completed work
            if any(keyword in text for keyword in ['database', 'schema', 'table', 'migration']):
                categories['database_setup'].append(task)
            elif any(keyword in text for keyword in ['auth', 'login', 'user', 'profile']):
                categories['authentication'].append(task)
            elif any(keyword in text for keyword in ['api', 'endpoint', 'service', 'backend']):
                categories['basic_apis'].append(task)
            elif any(keyword in text for keyword in ['component', 'ui component', 'reusable']):
                categories['core_components'].append(task)
            elif any(keyword in text for keyword in ['dashboard', 'admin', 'management']):
                categories['dashboard_features'].append(task)
            elif any(keyword in text for keyword in ['page', 'route', 'navigation']):
                categories['ui_pages'].append(task)
            elif any(keyword in text for keyword in ['calculator', 'business logic', 'algorithm']):
                categories['business_logic'].append(task)
            elif any(keyword in text for keyword in ['integration', 'external', 'api integration']):
                categories['integrations'].append(task)
            elif any(keyword in text for keyword in ['test', 'testing', 'quality']):
                categories['testing'].append(task)
            elif any(keyword in text for keyword in ['deploy', 'production', 'build']):
                categories['deployment'].append(task)
        
        # Remove empty categories
        categories = {k: v for k, v in categories.items() if v}
        
        return {
            'categories': categories,
            'capabilities_built': list(categories.keys()),
            'foundation_complete': self._is_foundation_complete(categories),
            'has_user_interface': bool(categories.get('ui_pages') or categories.get('dashboard_features')),
            'has_business_logic': bool(categories.get('business_logic')),
            'is_production_ready': bool(categories.get('testing') and categories.get('deployment'))
        }
    
    def _analyze_current_work(self, active_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze what's currently being worked on"""
        
        current_focus = {
            'infrastructure': [],
            'features': [],
            'ui_development': [],
            'optimization': []
        }
        
        for task in active_tasks:
            title = task.get('title', '').lower()
            description = task.get('description', '').lower()
            text = f"{title} {description}"
            
            if any(keyword in text for keyword in ['setup', 'config', 'database', 'auth']):
                current_focus['infrastructure'].append(task)
            elif any(keyword in text for keyword in ['feature', 'implement', 'calculator', 'logic']):
                current_focus['features'].append(task)
            elif any(keyword in text for keyword in ['ui', 'page', 'component', 'interface']):
                current_focus['ui_development'].append(task)
            elif any(keyword in text for keyword in ['optimize', 'improve', 'enhance', 'polish']):
                current_focus['optimization'].append(task)
        
        return {
            'focus_areas': {k: len(v) for k, v in current_focus.items() if v},
            'primary_focus': max(current_focus.keys(), key=lambda k: len(current_focus[k])) if any(current_focus.values()) else None,
            'active_tasks_by_category': current_focus
        }
    
    def _analyze_future_work(self, pending_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze what's planned for the future"""
        
        future_categories = {
            'planned_features': [],
            'planned_ui': [],
            'planned_optimization': [],
            'planned_testing': []
        }
        
        for task in pending_tasks:
            title = task.get('title', '').lower()
            description = task.get('description', '').lower()
            text = f"{title} {description}"
            
            if any(keyword in text for keyword in ['feature', 'implement', 'add']):
                future_categories['planned_features'].append(task)
            elif any(keyword in text for keyword in ['ui', 'page', 'interface']):
                future_categories['planned_ui'].append(task)
            elif any(keyword in text for keyword in ['optimize', 'improve', 'enhance']):
                future_categories['planned_optimization'].append(task)
            elif any(keyword in text for keyword in ['test', 'testing', 'quality']):
                future_categories['planned_testing'].append(task)
        
        return {
            'categories': {k: len(v) for k, v in future_categories.items() if v},
            'pending_work_by_category': future_categories
        }
    
    def _is_foundation_complete(self, completed_categories: Dict[str, List]) -> bool:
        """Determine if foundational work is complete"""
        foundation_indicators = ['database_setup', 'authentication', 'basic_apis']
        foundation_complete = any(completed_categories.get(indicator) for indicator in foundation_indicators)
        return foundation_complete
    
    def _assess_project_maturity(self, completed_work: Dict[str, Any], current_work: Dict[str, Any]) -> str:
        """Assess overall project maturity level"""
        
        if completed_work['foundation_complete'] and completed_work['has_user_interface']:
            if completed_work['is_production_ready']:
                return "mature"
            elif completed_work['has_business_logic']:
                return "intermediate"
            else:
                return "early_intermediate"
        elif completed_work['foundation_complete']:
            return "early"
        else:
            return "initial"
    
    def _identify_development_stage(self, completed_work: Dict[str, Any], current_work: Dict[str, Any]) -> str:
        """Identify what stage of development the project is in"""
        
        # Foundation stage
        if not completed_work['foundation_complete']:
            return "foundation_building"
        
        # Intelligence stage (core features)
        elif not completed_work['has_business_logic'] or current_work['primary_focus'] == 'features':
            return "feature_development"
        
        # Coordination stage (UI/UX)
        elif not completed_work['has_user_interface'] or current_work['primary_focus'] == 'ui_development':
            return "ui_coordination"
        
        # Optimization stage
        elif current_work['primary_focus'] == 'optimization' or completed_work['is_production_ready']:
            return "optimization_polish"
        
        else:
            return "transitional"


class Step2_PhaseCurrentStateMapper:
    """Step 2: Map current project state to appropriate phase progression"""
    
    async def map_to_phases(self, state_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Map the current project state to phase system"""
        
        logger.info("🎯 Step 2: Mapping project state to phase progression...")
        
        development_stage = state_analysis['development_stage']
        completed_work = state_analysis['completed_work']
        current_work = state_analysis['current_work']
        
        phase_mapping = {
            'current_phase': None,
            'completed_phases': [],
            'next_phase': None,
            'phase_recommendations': {},
            'reasoning': []
        }
        
        # Determine current phase based on development stage
        if development_stage == "foundation_building":
            phase_mapping['current_phase'] = 'phase_1_foundation'
            phase_mapping['reasoning'].append("Project is still building foundational infrastructure")
        
        elif development_stage == "feature_development":
            if completed_work['foundation_complete']:
                phase_mapping['completed_phases'].append('phase_1_foundation')
                phase_mapping['current_phase'] = 'phase_2_intelligence'
                phase_mapping['reasoning'].append("Foundation complete, actively developing core features")
            else:
                phase_mapping['current_phase'] = 'phase_1_foundation'
                phase_mapping['reasoning'].append("Foundation work mixed with feature development")
        
        elif development_stage == "ui_coordination":
            phase_mapping['completed_phases'].extend(['phase_1_foundation', 'phase_2_intelligence'])
            phase_mapping['current_phase'] = 'phase_3_coordination'
            phase_mapping['reasoning'].append("Core features exist, focusing on UI and coordination")
        
        elif development_stage == "optimization_polish":
            phase_mapping['completed_phases'].extend(['phase_1_foundation', 'phase_2_intelligence', 'phase_3_coordination'])
            phase_mapping['current_phase'] = 'phase_4_optimization'
            phase_mapping['reasoning'].append("System is built, focusing on optimization and polish")
        
        else:  # transitional
            # Make best guess based on completed work
            if completed_work['has_user_interface'] and completed_work['has_business_logic']:
                phase_mapping['completed_phases'].extend(['phase_1_foundation', 'phase_2_intelligence'])
                phase_mapping['current_phase'] = 'phase_3_coordination'
            elif completed_work['has_business_logic']:
                phase_mapping['completed_phases'].append('phase_1_foundation')
                phase_mapping['current_phase'] = 'phase_2_intelligence'
            elif completed_work['foundation_complete']:
                phase_mapping['current_phase'] = 'phase_2_intelligence'
            else:
                phase_mapping['current_phase'] = 'phase_1_foundation'
            
            phase_mapping['reasoning'].append("Transitional state - mapped based on completed capabilities")
        
        # Determine next phase
        phase_order = ['phase_1_foundation', 'phase_2_intelligence', 'phase_3_coordination', 'phase_4_optimization']
        current_index = phase_order.index(phase_mapping['current_phase']) if phase_mapping['current_phase'] in phase_order else 0
        
        if current_index < len(phase_order) - 1:
            phase_mapping['next_phase'] = phase_order[current_index + 1]
        
        # Create phase recommendations
        phase_mapping['phase_recommendations'] = self._create_phase_recommendations(
            phase_mapping, state_analysis
        )
        
        logger.info(f"   Current phase: {phase_mapping['current_phase']}")
        logger.info(f"   Completed phases: {phase_mapping['completed_phases']}")
        logger.info(f"   Next phase: {phase_mapping['next_phase']}")
        
        return phase_mapping
    
    def _create_phase_recommendations(self, phase_mapping: Dict[str, Any], 
                                   state_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create specific recommendations for each phase"""
        
        recommendations = {}
        
        # Foundation phase recommendations
        if 'phase_1_foundation' not in phase_mapping['completed_phases']:
            foundation_work = []
            if not state_analysis['completed_work']['capabilities_built']:
                foundation_work.extend(['database setup', 'authentication', 'basic APIs'])
            recommendations['phase_1_foundation'] = {
                'status': 'needed',
                'work_required': foundation_work
            }
        else:
            recommendations['phase_1_foundation'] = {
                'status': 'completed',
                'work_required': []
            }
        
        # Intelligence phase recommendations  
        if phase_mapping['current_phase'] == 'phase_2_intelligence':
            intelligence_work = []
            if not state_analysis['completed_work']['has_business_logic']:
                intelligence_work.extend(['core business logic', 'algorithms', 'data processing'])
            recommendations['phase_2_intelligence'] = {
                'status': 'active',
                'work_required': intelligence_work
            }
        elif 'phase_2_intelligence' in phase_mapping['completed_phases']:
            recommendations['phase_2_intelligence'] = {
                'status': 'completed',
                'work_required': []
            }
        
        return recommendations


class Step3_TaskCategorizer:
    """Step 3: Categorize tasks based on current project understanding"""
    
    async def categorize_tasks(self, all_tasks: List[Dict[str, Any]], 
                             phase_mapping: Dict[str, Any]) -> Dict[str, Any]:
        """Categorize tasks based on project state understanding"""
        
        logger.info("📋 Step 3: Categorizing tasks based on project state...")
        
        categorization = {
            'foundation_tasks': [],
            'intelligence_tasks': [],
            'coordination_tasks': [],
            'optimization_tasks': [],
            'completed_foundation': [],
            'completed_intelligence': [],
            'completed_coordination': [],
            'active_tasks': [],
            'future_tasks': []
        }
        
        for task in all_tasks:
            status = task.get('status', '')
            title = task.get('title', '').lower()
            description = task.get('description', '').lower()
            text = f"{title} {description}"
            
            # First categorize by completion status and phase
            if status == 'completed':
                category = self._categorize_completed_task(text)
                categorization[f'completed_{category}'].append(task)
            elif status == 'in_progress':
                category = self._categorize_active_task(text, phase_mapping)
                categorization[f'{category}_tasks'].append(task)
                categorization['active_tasks'].append(task)
            elif status == 'pending':
                category = self._categorize_future_task(text, phase_mapping)
                categorization[f'{category}_tasks'].append(task)
                categorization['future_tasks'].append(task)
            else:  # cancelled, etc.
                # Still categorize for understanding
                category = self._categorize_completed_task(text)
                categorization[f'completed_{category}'].append(task)
        
        # Log categorization results
        for category, tasks in categorization.items():
            if tasks and 'tasks' in category:
                logger.info(f"   {category}: {len(tasks)} tasks")
        
        return categorization
    
    def _categorize_completed_task(self, text: str) -> str:
        """Categorize a completed task to understand what phase it belongs to"""
        
        # Foundation indicators
        if any(keyword in text for keyword in [
            'setup', 'config', 'database', 'schema', 'auth', 'authentication',
            'basic', 'core setup', 'infrastructure', 'migration'
        ]):
            return 'foundation'
        
        # Intelligence indicators  
        elif any(keyword in text for keyword in [
            'calculator', 'algorithm', 'business logic', 'processing',
            'computation', 'feature logic', 'core feature'
        ]):
            return 'intelligence'
        
        # Coordination indicators
        elif any(keyword in text for keyword in [
            'page', 'component', 'ui', 'interface', 'dashboard',
            'navigation', 'form', 'layout', 'integration'
        ]):
            return 'coordination'
        
        # Default to foundation for unknown completed work
        else:
            return 'foundation'
    
    def _categorize_active_task(self, text: str, phase_mapping: Dict[str, Any]) -> str:
        """Categorize an active task based on current phase context"""
        
        current_phase = phase_mapping.get('current_phase', 'phase_1_foundation')
        
        # Use current phase as primary hint
        if current_phase == 'phase_1_foundation':
            return 'foundation'
        elif current_phase == 'phase_2_intelligence':
            return 'intelligence'
        elif current_phase == 'phase_3_coordination':
            return 'coordination'
        elif current_phase == 'phase_4_optimization':
            return 'optimization'
        else:
            # Fallback to content analysis
            return self._categorize_completed_task(text)
    
    def _categorize_future_task(self, text: str, phase_mapping: Dict[str, Any]) -> str:
        """Categorize a future task based on what phases are planned"""
        
        next_phase = phase_mapping.get('next_phase')
        
        # Use next phase as primary hint
        if next_phase == 'phase_2_intelligence':
            return 'intelligence'
        elif next_phase == 'phase_3_coordination':
            return 'coordination'
        elif next_phase == 'phase_4_optimization':
            return 'optimization'
        else:
            # Fallback to content analysis
            return self._categorize_completed_task(text)


class Step4_PhaseStructureBuilder:
    """Step 4: Build the actual phase structure for migration"""
    
    def _identify_workstreams(self, tasks: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """Identify logical workstreams from tasks"""
        workstreams = {}
        
        # Define workstream patterns with multiple indicators
        workstream_patterns = {
            'quote_calculator': {
                'keywords': ['quote', 'calculator', 'pricing', 'estimate', 'quotation'],
                'patterns': [r'quote\s+calculator', r'pricing\s+logic', r'quote\s+system'],
                'min_score': 1
            },
            'authentication': {
                'keywords': ['auth', 'login', 'user', 'profile', 'session', 'authentication', 'signup', 'signin'],
                'patterns': [r'user\s+management', r'authentication\s+system', r'login\s+system'],
                'min_score': 2
            },
            'dashboard': {
                'keywords': ['dashboard', 'admin', 'management', 'overview', 'analytics'],
                'patterns': [r'admin\s+dashboard', r'management\s+interface'],
                'min_score': 1
            },
            'api_development': {
                'keywords': ['api', 'endpoint', 'service', 'backend', 'rest', 'graphql'],
                'patterns': [r'api\s+endpoint', r'backend\s+service', r'rest\s+api'],
                'min_score': 1
            },
            'database': {
                'keywords': ['database', 'schema', 'table', 'migration', 'sql', 'db'],
                'patterns': [r'database\s+schema', r'data\s+model', r'table\s+structure'],
                'min_score': 1
            },
            'ui_development': {
                'keywords': ['ui', 'component', 'page', 'interface', 'frontend', 'view', 'screen'],
                'patterns': [r'ui\s+component', r'user\s+interface', r'frontend\s+page'],
                'min_score': 2
            },
            'testing': {
                'keywords': ['test', 'testing', 'quality', 'qa', 'unit', 'integration', 'e2e'],
                'patterns': [r'unit\s+test', r'integration\s+test', r'test\s+suite'],
                'min_score': 1
            },
            'deployment': {
                'keywords': ['deploy', 'deployment', 'production', 'release', 'build', 'ci', 'cd'],
                'patterns': [r'deployment\s+pipeline', r'ci/cd', r'production\s+release'],
                'min_score': 1
            }
        }
        
        # Score each task against workstream patterns
        for task in tasks:
            title = task.get('title', '').lower()
            description = task.get('description', '').lower()
            full_text = f"{title} {description}"
            
            best_score = 0
            best_workstream = None
            
            for workstream_key, pattern_info in workstream_patterns.items():
                score = 0
                
                # Check keywords
                for keyword in pattern_info['keywords']:
                    if keyword in full_text:
                        score += 1
                
                # Check regex patterns
                for pattern in pattern_info['patterns']:
                    if re.search(pattern, full_text, re.IGNORECASE):
                        score += 2  # Patterns are more specific, so higher weight
                
                # Update best match if score meets minimum
                if score >= pattern_info['min_score'] and score > best_score:
                    best_score = score
                    best_workstream = workstream_key
            
            # If no good match, use general category
            if not best_workstream:
                workstream_key = 'general'
            else:
                workstream_key = best_workstream
            
            if workstream_key not in workstreams:
                workstreams[workstream_key] = []
            workstreams[workstream_key].append(task)
        
        # Consolidate small workstreams
        consolidated_workstreams = {}
        general_tasks = workstreams.get('general', [])
        
        for workstream_key, tasks_list in workstreams.items():
            if workstream_key == 'general':
                continue
                
            # If workstream has fewer than 3 tasks, merge into general
            if len(tasks_list) < 3:
                general_tasks.extend(tasks_list)
                logger.info(f"   Consolidating small workstream '{workstream_key}' ({len(tasks_list)} tasks) into general")
            else:
                consolidated_workstreams[workstream_key] = tasks_list
        
        # Only include general if it has tasks
        if general_tasks:
            consolidated_workstreams['general'] = general_tasks
        
        # If we end up with too many workstreams, further consolidate
        if len(consolidated_workstreams) > 7:
            logger.info(f"   Too many workstreams ({len(consolidated_workstreams)}), applying further consolidation...")
            
            # Sort by task count and keep top 6, merge rest into general
            sorted_workstreams = sorted(consolidated_workstreams.items(), 
                                      key=lambda x: len(x[1]), 
                                      reverse=True)
            
            final_workstreams = {}
            general_overflow = []
            
            for i, (ws_key, ws_tasks) in enumerate(sorted_workstreams):
                if i < 6:
                    final_workstreams[ws_key] = ws_tasks
                else:
                    general_overflow.extend(ws_tasks)
            
            if general_overflow:
                if 'general' in final_workstreams:
                    final_workstreams['general'].extend(general_overflow)
                else:
                    final_workstreams['general'] = general_overflow
            
            return final_workstreams
        
        return consolidated_workstreams
    
    async def build_phase_structure(self, phase_mapping: Dict[str, Any], 
                                   task_categorization: Dict[str, Any],
                                   all_tasks: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build the phase structure for migration"""
        
        logger.info("🏗️ Step 4: Building phase structure with relationship-aware workstream analysis...")
        
        # Use relationship-aware migration if all_tasks provided
        if all_tasks:
            # Filter out cancelled tasks
            active_tasks = [t for t in all_tasks if t.get('status') != 'cancelled']
            
            relationship_migration = RelationshipAwareMigration(active_tasks, phase_mapping)
            relationship_structure = await relationship_migration.create_workstream_structure()
            
            # Extract mappings from relationship analysis
            workstream_mappings = relationship_structure['workstream_mappings']
            task_assignments = relationship_structure['task_assignments']
            
            logger.info(f"   Relationship analysis found {len(workstream_mappings)} natural workstreams")
            logger.info(f"   All {len(task_assignments)} tasks assigned (no orphans!)")
            
            # Create phase structures
            phases_to_create = self._create_phases_from_workstreams(workstream_mappings, phase_mapping)
            
            structure = {
                'phases_to_create': phases_to_create,
                'task_assignments': task_assignments,
                'workstream_mappings': workstream_mappings,
                'migration_strategy': {
                    'preserve_hierarchy': True,
                    'relationship_based': True,
                    'no_orphans': True,
                    'reasoning': [
                        "Used relationship analysis to identify natural task clusters",
                        "Preserved parent-child relationships within workstreams",
                        "Ensured every task is assigned to a workstream",
                        "Created workstreams only where tasks exist"
                    ]
                }
            }
            
            return structure
        
        # Fallback to original logic if no all_tasks provided
        phases_to_create = []
        task_assignments = {}
        workstream_mappings = {}  # Maps tasks to their workstream root tasks
        
        # Determine which phases need to be created
        current_phase = phase_mapping.get('current_phase')
        completed_phases = phase_mapping.get('completed_phases', [])
        
        # Create completed phases (marked as completed)
        for phase_id in completed_phases:
            phase_info = self._get_phase_info(phase_id)
            phase_info['status'] = 'completed'
            phase_tasks = self._get_tasks_for_phase(phase_id, task_categorization, completed=True)
            phase_info['tasks'] = phase_tasks
            
            # Identify workstreams within this phase
            workstreams = self._identify_workstreams(phase_tasks)
            phase_info['workstreams'] = workstreams
            phase_info['workstream_count'] = len(workstreams)
            
            phases_to_create.append(phase_info)
            
            # Create workstream mapping for migration
            for workstream_key, workstream_tasks in workstreams.items():
                workstream_root_id = f"root_{phase_id}_{workstream_key}"
                workstream_mappings[workstream_root_id] = {
                    'phase_id': phase_id,
                    'workstream_key': workstream_key,
                    'tasks': workstream_tasks,
                    'title': self._create_workstream_title(workstream_key)
                }
                
                # Assign tasks to workstream root (to be created during migration)
                for task in workstream_tasks:
                    task_assignments[task['task_id']] = workstream_root_id
        
        # Create current active phase
        if current_phase:
            phase_info = self._get_phase_info(current_phase)
            phase_info['status'] = 'in_progress'
            phase_tasks = self._get_tasks_for_phase(current_phase, task_categorization, completed=False)
            phase_info['tasks'] = phase_tasks
            
            # Identify workstreams within this phase
            workstreams = self._identify_workstreams(phase_tasks)
            phase_info['workstreams'] = workstreams
            phase_info['workstream_count'] = len(workstreams)
            
            phases_to_create.append(phase_info)
            
            # Create workstream mapping for migration
            for workstream_key, workstream_tasks in workstreams.items():
                workstream_root_id = f"root_{current_phase}_{workstream_key}"
                workstream_mappings[workstream_root_id] = {
                    'phase_id': current_phase,
                    'workstream_key': workstream_key,
                    'tasks': workstream_tasks,
                    'title': self._create_workstream_title(workstream_key)
                }
                
                # Assign tasks to workstream root (to be created during migration)
                for task in workstream_tasks:
                    task_assignments[task['task_id']] = workstream_root_id
        
        # Ensure ALL tasks get assigned to a workstream
        if all_tasks:
            # Get all task IDs from the database
            all_task_ids_from_db = {task['task_id'] for task in all_tasks 
                                   if not task['task_id'].startswith('phase_')}  # Exclude phase tasks
            
            assigned_task_ids = set(task_assignments.keys())
            unassigned_task_ids = all_task_ids_from_db - assigned_task_ids
            
            if unassigned_task_ids:
                logger.info(f"   Found {len(unassigned_task_ids)} unassigned tasks, assigning to appropriate workstreams")
                
                # Group unassigned tasks by their status
                unassigned_tasks = [task for task in all_tasks if task['task_id'] in unassigned_task_ids]
                
                # Categorize these unassigned tasks
                for task in unassigned_tasks:
                    # Determine which phase this task should belong to based on status
                    if task['status'] == 'cancelled':
                        continue  # Skip cancelled tasks
                    
                    task_phase = None
                    if task['status'] == 'completed':
                        # Completed tasks likely belong to foundation phase
                        task_phase = 'phase_1_foundation'
                    elif task['status'] in ['in_progress', 'pending']:
                        # Active/pending tasks belong to current phase
                        task_phase = current_phase or 'phase_2_intelligence'
                    
                    if task_phase:
                        # Try to categorize the task into an existing workstream
                        workstream_key = self._categorize_single_task(task)
                        workstream_root_id = f"root_{task_phase}_{workstream_key}"
                        
                        # If workstream doesn't exist, create it
                        if workstream_root_id not in workstream_mappings:
                            workstream_mappings[workstream_root_id] = {
                                'phase_id': task_phase,
                                'workstream_key': workstream_key,
                                'tasks': [],
                                'title': self._create_workstream_title(workstream_key)
                            }
                        
                        # Assign task to workstream
                        task_assignments[task['task_id']] = workstream_root_id
                        workstream_mappings[workstream_root_id]['tasks'].append(task)
        
        structure = {
            'phases_to_create': phases_to_create,
            'task_assignments': task_assignments,
            'workstream_mappings': workstream_mappings,  # New: Maps workstream roots to their tasks
            'migration_strategy': self._determine_migration_strategy(phase_mapping, task_categorization)
        }
        
        logger.info(f"   Phases to create: {len(phases_to_create)}")
        for phase in phases_to_create:
            logger.info(f"   - {phase['name']}: {len(phase['tasks'])} tasks in {phase.get('workstream_count', 0)} workstreams ({phase['status']})")
        
        logger.info(f"   Total workstreams identified: {len(workstream_mappings)}")
        
        return structure
    
    def _categorize_single_task(self, task: Dict[str, Any]) -> str:
        """Categorize a single task into a workstream"""
        title = task.get('title', '').lower()
        description = task.get('description', '').lower()
        full_text = f"{title} {description}"
        
        # Use same logic as _identify_workstreams but for single task
        workstream_patterns = {
            'quote_calculator': {
                'keywords': ['quote', 'calculator', 'pricing', 'estimate', 'quotation'],
                'patterns': [r'quote\s+calculator', r'pricing\s+logic', r'quote\s+system'],
                'min_score': 1
            },
            'authentication': {
                'keywords': ['auth', 'login', 'user', 'profile', 'session', 'authentication', 'signup', 'signin'],
                'patterns': [r'user\s+management', r'authentication\s+system', r'login\s+system'],
                'min_score': 2
            },
            'dashboard': {
                'keywords': ['dashboard', 'admin', 'management', 'overview', 'analytics'],
                'patterns': [r'admin\s+dashboard', r'management\s+interface'],
                'min_score': 1
            },
            'api_development': {
                'keywords': ['api', 'endpoint', 'service', 'backend', 'rest', 'graphql'],
                'patterns': [r'api\s+endpoint', r'backend\s+service', r'rest\s+api'],
                'min_score': 1
            },
            'database': {
                'keywords': ['database', 'schema', 'table', 'migration', 'sql', 'db'],
                'patterns': [r'database\s+schema', r'data\s+model', r'table\s+structure'],
                'min_score': 1
            },
            'ui_development': {
                'keywords': ['ui', 'component', 'page', 'interface', 'frontend', 'view', 'screen'],
                'patterns': [r'ui\s+component', r'user\s+interface', r'frontend\s+page'],
                'min_score': 2
            },
            'testing': {
                'keywords': ['test', 'testing', 'quality', 'qa', 'unit', 'integration', 'e2e'],
                'patterns': [r'unit\s+test', r'integration\s+test', r'test\s+suite'],
                'min_score': 1
            },
            'deployment': {
                'keywords': ['deploy', 'deployment', 'production', 'release', 'build', 'ci', 'cd'],
                'patterns': [r'deployment\s+pipeline', r'ci/cd', r'production\s+release'],
                'min_score': 1
            }
        }
        
        best_score = 0
        best_workstream = None
        
        for workstream_key, pattern_info in workstream_patterns.items():
            score = 0
            
            # Check keywords
            for keyword in pattern_info['keywords']:
                if keyword in full_text:
                    score += 1
            
            # Check regex patterns
            for pattern in pattern_info['patterns']:
                if re.search(pattern, full_text, re.IGNORECASE):
                    score += 2  # Patterns are more specific, so higher weight
            
            # Update best match if score meets minimum
            if score >= pattern_info['min_score'] and score > best_score:
                best_score = score
                best_workstream = workstream_key
        
        return best_workstream or 'general'
    
    def _create_phases_from_workstreams(self, workstream_mappings: Dict[str, Any], 
                                       phase_mapping: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create phase structures from workstream mappings"""
        phases_to_create = []
        phase_info_map = {}
        
        # Group workstreams by phase
        for ws_id, ws_info in workstream_mappings.items():
            phase_id = ws_info['phase_id']
            
            if phase_id not in phase_info_map:
                # Create phase info
                phase_info = self._get_phase_info(phase_id)
                
                # Determine phase status
                if phase_id in phase_mapping.get('completed_phases', []):
                    phase_info['status'] = 'completed'
                elif phase_id == phase_mapping.get('current_phase'):
                    phase_info['status'] = 'in_progress'
                else:
                    phase_info['status'] = 'pending'
                
                phase_info['workstreams'] = {}
                phase_info['tasks'] = []
                phase_info_map[phase_id] = phase_info
                phases_to_create.append(phase_info)
            
            # Add workstream to phase
            ws_key = ws_info['workstream_key']
            phase_info_map[phase_id]['workstreams'][ws_key] = ws_info['tasks']
            phase_info_map[phase_id]['tasks'].extend(ws_info['tasks'])
        
        # Update workstream counts
        for phase_info in phases_to_create:
            phase_info['workstream_count'] = len(phase_info['workstreams'])
        
        return phases_to_create
    
    def _create_workstream_title(self, workstream_key: str) -> str:
        """Create a human-readable title for a workstream"""
        
        title_map = {
            'quote_calculator': 'Quote Calculator System',
            'authentication': 'Authentication & User Management',
            'dashboard': 'Dashboard Features',
            'api_development': 'API Development',
            'database': 'Database Architecture',
            'ui_development': 'UI Components & Pages',
            'testing': 'Testing Framework',
            'deployment': 'Deployment & DevOps',
            'general': 'General Tasks'
        }
        
        if workstream_key in title_map:
            return title_map[workstream_key]
        
        # Fallback: Capitalize and replace underscores
        return workstream_key.replace('_', ' ').title()
    
    def _get_phase_info(self, phase_id: str) -> Dict[str, Any]:
        """Get phase information"""
        
        phase_definitions = {
            'phase_1_foundation': {
                'phase_id': 'phase_1_foundation',
                'name': 'Phase 1: Foundation',
                'description': 'Core system architecture, database, authentication, and basic APIs'
            },
            'phase_2_intelligence': {
                'phase_id': 'phase_2_intelligence', 
                'name': 'Phase 2: Intelligence',
                'description': 'Core business logic, algorithms, and intelligent features'
            },
            'phase_3_coordination': {
                'phase_id': 'phase_3_coordination',
                'name': 'Phase 3: Coordination', 
                'description': 'User interface, integration, and system coordination'
            },
            'phase_4_optimization': {
                'phase_id': 'phase_4_optimization',
                'name': 'Phase 4: Optimization',
                'description': 'Performance tuning, testing, and production optimization'
            }
        }
        
        return phase_definitions.get(phase_id, {})
    
    def _get_tasks_for_phase(self, phase_id: str, task_categorization: Dict[str, Any], 
                           completed: bool = False) -> List[Dict[str, Any]]:
        """Get tasks that belong to a specific phase"""
        
        phase_map = {
            'phase_1_foundation': 'foundation',
            'phase_2_intelligence': 'intelligence', 
            'phase_3_coordination': 'coordination',
            'phase_4_optimization': 'optimization'
        }
        
        category = phase_map.get(phase_id, 'foundation')
        
        if completed:
            return task_categorization.get(f'completed_{category}', [])
        else:
            return (task_categorization.get(f'{category}_tasks', []) + 
                   task_categorization.get(f'completed_{category}', []))
    
    def _determine_migration_strategy(self, phase_mapping: Dict[str, Any], 
                                    task_categorization: Dict[str, Any]) -> Dict[str, Any]:
        """Determine the best migration strategy"""
        
        return {
            'preserve_hierarchy': True,
            'mark_completed_phases': len(phase_mapping.get('completed_phases', [])) > 0,
            'focus_on_current_phase': True,
            'create_workstream_roots': True,  # New: Create multiple root tasks per phase
            'reasoning': [
                "Preserve existing task hierarchies within phases",
                "Mark phases as completed if foundational work is done",
                "Focus migration on current active development phase",
                "Create logical workstreams as root tasks for better organization"
            ]
        }


class GranularMigrationManager:
    """Orchestrates the granular multi-step migration process"""
    
    def __init__(self):
        self.step1_analyzer = Step1_ProjectStateAnalyzer()
        self.step2_mapper = Step2_PhaseCurrentStateMapper()
        self.step3_categorizer = Step3_TaskCategorizer()
        self.step4_builder = Step4_PhaseStructureBuilder()
    
    async def run_granular_migration(self) -> bool:
        """Run the complete granular migration process"""
        try:
            logger.info("🔧 Starting granular multi-step migration process...")
            
            # Check if migration is needed
            if not self._needs_migration():
                return True
            
            # Load all tasks
            all_tasks = self._load_all_tasks()
            if not all_tasks:
                logger.info("ℹ️ No tasks found to migrate")
                return True
            
            logger.info(f"📊 Loaded {len(all_tasks)} tasks for granular analysis")
            
            # Step 1: Analyze current project state
            state_analysis = await self.step1_analyzer.analyze_current_state(all_tasks)
            
            # Step 2: Map to phase progression
            phase_mapping = await self.step2_mapper.map_to_phases(state_analysis)
            
            # Step 3: Categorize tasks
            task_categorization = await self.step3_categorizer.categorize_tasks(all_tasks, phase_mapping)
            
            # Step 4: Build phase structure (pass all_tasks for complete coverage)
            phase_structure = await self.step4_builder.build_phase_structure(phase_mapping, task_categorization, all_tasks)
            
            # Step 5: Execute migration
            logger.info("🚀 Step 5: Executing granular migration...")
            success = await self._execute_granular_migration(phase_structure)
            
            if success:
                logger.info("✅ Granular migration completed successfully!")
                return True
            else:
                logger.error("❌ Granular migration failed!")
                return False
                
        except Exception as e:
            logger.error(f"Critical error during granular migration: {e}")
            return False
    
    def _needs_migration(self) -> bool:
        """Check if migration is needed"""
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
    
    async def _execute_granular_migration(self, phase_structure: Dict[str, Any]) -> bool:
        """Execute the granular migration"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Create phases
            for phase_info in phase_structure['phases_to_create']:
                await self._create_phase(cursor, phase_info)
            
            # Create workstream root tasks (only if they have tasks)
            workstream_mappings = phase_structure.get('workstream_mappings', {})
            created_workstreams = 0
            skipped_workstreams = 0
            
            for workstream_root_id, workstream_info in workstream_mappings.items():
                # Only create workstream if it has tasks to migrate
                if len(workstream_info.get('tasks', [])) > 0:
                    await self._create_workstream_root(cursor, workstream_root_id, workstream_info)
                    created_workstreams += 1
                else:
                    logger.warning(f"   Skipping empty workstream: {workstream_info.get('title', workstream_root_id)}")
                    skipped_workstreams += 1
            
            # Migrate tasks
            migrated_count = 0
            for task_id, parent_id in phase_structure['task_assignments'].items():
                if await self._migrate_task(cursor, task_id, parent_id):
                    migrated_count += 1
            
            conn.commit()
            conn.close()
            
            logger.info(f"   ✅ Created {created_workstreams} workstream root tasks")
            if skipped_workstreams > 0:
                logger.info(f"   ⚠️  Skipped {skipped_workstreams} empty workstreams")
            logger.info(f"   ✅ Migrated {migrated_count} tasks to workstreams")
            return True
            
        except Exception as e:
            logger.error(f"Error executing granular migration: {e}")
            return False
    
    async def _create_workstream_root(self, cursor, workstream_root_id: str, workstream_info: Dict[str, Any]) -> None:
        """Create a workstream root task"""
        
        created_at = datetime.datetime.now().isoformat()
        phase_id = workstream_info['phase_id']
        title = workstream_info['title']
        task_count = len(workstream_info.get('tasks', []))
        
        # Create a description based on the workstream's tasks
        task_titles = [t.get('title', '') for t in workstream_info.get('tasks', [])[:3]]
        description = f"Workstream containing {task_count} related tasks"
        if task_titles:
            description += f" including: {', '.join(task_titles[:2])}"
            if task_count > 2:
                description += f" and {task_count - 2} more"
        
        initial_notes = [{
            "timestamp": created_at,
            "author": "granular_migration",
            "content": f"🚀 Workstream root task created during migration. Groups {task_count} related tasks."
        }]
        
        # Determine workstream status based on child tasks
        workstream_status = "pending"
        if workstream_info.get('tasks'):
            task_statuses = [t.get('status', 'pending') for t in workstream_info['tasks']]
            if all(status == 'completed' for status in task_statuses):
                workstream_status = "completed"
            elif any(status == 'in_progress' for status in task_statuses):
                workstream_status = "in_progress"
            elif any(status == 'completed' for status in task_statuses):
                workstream_status = "in_progress"  # Some completed means work has started
        
        root_task_data = {
            "task_id": workstream_root_id,
            "title": title,
            "description": description,
            "assigned_to": None,
            "created_by": "granular_migration",
            "status": workstream_status,
            "priority": "high",
            "created_at": created_at,
            "updated_at": created_at,
            "parent_task": phase_id,  # Root task belongs to phase
            "child_tasks": json.dumps([]),
            "depends_on_tasks": json.dumps([]),
            "notes": json.dumps(initial_notes)
        }
        
        cursor.execute("""
            INSERT INTO tasks (task_id, title, description, assigned_to, created_by, status, priority,
                             created_at, updated_at, parent_task, child_tasks, depends_on_tasks, notes)
            VALUES (:task_id, :title, :description, :assigned_to, :created_by, :status, :priority,
                    :created_at, :updated_at, :parent_task, :child_tasks, :depends_on_tasks, :notes)
        """, root_task_data)
        
        # Update phase's child_tasks to include this root task
        cursor.execute("SELECT child_tasks FROM tasks WHERE task_id = ?", (phase_id,))
        phase_children = json.loads(cursor.fetchone()["child_tasks"] or "[]")
        phase_children.append(workstream_root_id)
        cursor.execute("UPDATE tasks SET child_tasks = ? WHERE task_id = ?", 
                      (json.dumps(phase_children), phase_id))
        
        logger.info(f"      Created root task: {title} ({workstream_root_id})")
    
    async def _create_phase(self, cursor, phase_info: Dict[str, Any]) -> None:
        """Create a phase with proper status"""
        
        phase_id = phase_info['phase_id']
        
        # Check if already exists
        cursor.execute("SELECT task_id FROM tasks WHERE task_id = ?", (phase_id,))
        if cursor.fetchone():
            return
        
        created_at = datetime.datetime.now().isoformat()
        status = phase_info.get('status', 'pending')
        
        initial_notes = [{
            "timestamp": created_at,
            "author": "granular_migration",
            "content": f"🔧 Granular migration: Phase created with status '{status}' based on project state analysis. Contains {len(phase_info.get('tasks', []))} tasks."
        }]
        
        phase_data = {
            "task_id": phase_id,
            "title": phase_info['name'],
            "description": phase_info['description'],
            "assigned_to": None,
            "created_by": "granular_migration",
            "status": status,
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
        
        logger.info(f"   📊 Created {phase_info['name']} (status: {status})")
    
    async def _migrate_task(self, cursor, task_id: str, parent_id: str) -> bool:
        """Migrate a task to a workstream root or phase"""
        try:
            cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            task = cursor.fetchone()
            if not task:
                return False
            
            task = dict(task)
            current_parent = task.get('parent_task')
            
            # With relationship-aware migration, we preserve hierarchies
            # Only update parent if task has no parent or parent is phase/root
            should_update_parent = (
                not current_parent or
                current_parent.startswith(('phase_', 'root_')) or
                current_parent not in [row['task_id'] for row in cursor.execute("SELECT task_id FROM tasks")]
            )
            
            updated_at = datetime.datetime.now().isoformat()
            
            # Add migration note
            current_notes = json.loads(task.get('notes', '[]'))
            migration_note = {
                "timestamp": updated_at,
                "author": "granular_migration",
                "content": f"🔧 Relationship-aware migration: Task organized under {parent_id} workstream. Hierarchy preserved."
            }
            current_notes.append(migration_note)
            
            if should_update_parent:
                # Update task parent to workstream root
                cursor.execute("""
                    UPDATE tasks 
                    SET parent_task = ?, updated_at = ?, notes = ?
                    WHERE task_id = ?
                """, (parent_id, updated_at, json.dumps(current_notes), task_id))
                
                # Update parent's child_tasks list
                cursor.execute("SELECT child_tasks FROM tasks WHERE task_id = ?", (parent_id,))
                parent_row = cursor.fetchone()
                if parent_row:
                    parent_children = json.loads(parent_row["child_tasks"] or "[]")
                    if task_id not in parent_children:
                        parent_children.append(task_id)
                        cursor.execute("UPDATE tasks SET child_tasks = ? WHERE task_id = ?", 
                                      (json.dumps(parent_children), parent_id))
            else:
                # Just update notes to indicate migration
                cursor.execute("""
                    UPDATE tasks 
                    SET updated_at = ?, notes = ?
                    WHERE task_id = ?
                """, (updated_at, json.dumps(current_notes), task_id))
                
                # Ensure the task's parent is also being migrated to same workstream
                if current_parent:
                    # This maintains the hierarchy within the workstream
                    pass
            
            return True
            
        except Exception as e:
            logger.error(f"Error migrating task {task_id}: {e}")
            return False


async def run_granular_migration() -> bool:
    """Entry point for granular migration"""
    migration_manager = GranularMigrationManager()
    return await migration_manager.run_granular_migration()