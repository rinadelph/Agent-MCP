#!/usr/bin/env python3
"""
Relationship-Aware Migration System

This module analyzes task relationships and dependencies to create
natural workstream clusters while preserving hierarchies.
"""

import json
import re
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict
from .config import logger


class TaskRelationshipAnalyzer:
    """Analyzes task relationships to identify natural clusters"""
    
    def __init__(self, all_tasks: List[Dict[str, Any]]):
        self.tasks = {task['task_id']: task for task in all_tasks}
        self.children_map = defaultdict(list)  # parent_id -> [child_ids]
        self.parent_map = {}  # child_id -> parent_id
        self.dependency_map = defaultdict(set)  # task_id -> {dependent_ids}
        self.clusters = {}  # cluster_id -> {task_ids}
        
    def analyze_relationships(self) -> Dict[str, Any]:
        """Analyze all task relationships and create clusters"""
        logger.info("🔍 Analyzing task relationships and dependencies...")
        
        # Step 1: Build relationship maps
        self._build_relationship_maps()
        
        # Step 2: Identify root tasks (tasks with no parent or phase/root parents)
        root_tasks = self._identify_root_tasks()
        
        # Step 3: Build task clusters based on relationships
        clusters = self._build_task_clusters(root_tasks)
        
        # Step 4: Analyze cluster characteristics
        cluster_analysis = self._analyze_clusters(clusters)
        
        return {
            'clusters': clusters,
            'cluster_analysis': cluster_analysis,
            'relationship_stats': {
                'total_tasks': len(self.tasks),
                'root_tasks': len(root_tasks),
                'tasks_with_children': len(self.children_map),
                'tasks_with_dependencies': len(self.dependency_map),
                'natural_clusters': len(clusters)
            }
        }
    
    def _build_relationship_maps(self):
        """Build maps of parent-child and dependency relationships"""
        for task_id, task in self.tasks.items():
            # Skip phase tasks
            if task_id.startswith('phase_'):
                continue
                
            # Parent-child relationships
            parent_id = task.get('parent_task')
            if parent_id and not parent_id.startswith(('phase_', 'root_')):
                self.parent_map[task_id] = parent_id
                self.children_map[parent_id].append(task_id)
            
            # Dependency relationships
            depends_on = task.get('depends_on_tasks', '[]')
            if isinstance(depends_on, str):
                depends_on = json.loads(depends_on)
            for dep_id in depends_on:
                if dep_id in self.tasks:
                    self.dependency_map[task_id].add(dep_id)
    
    def _identify_root_tasks(self) -> List[str]:
        """Identify tasks that are roots of their hierarchies"""
        root_tasks = []
        
        for task_id, task in self.tasks.items():
            # Skip phase and root tasks
            if task_id.startswith(('phase_', 'root_')):
                continue
                
            parent_id = task.get('parent_task')
            
            # Task is a root if:
            # 1. It has no parent
            # 2. Its parent is a phase or root task (from previous migration)
            # 3. Its parent doesn't exist (broken hierarchy)
            # 4. Its parent is cancelled (treat as orphan)
            parent_task = self.tasks.get(parent_id) if parent_id else None
            parent_cancelled = parent_task and parent_task.get('status') == 'cancelled'
            
            is_root = (
                not parent_id or
                parent_cancelled or
                (parent_id and parent_id.startswith(('phase_', 'root_'))) or
                (parent_id and parent_id not in self.tasks)
            )
            
            if is_root:
                root_tasks.append(task_id)
                
        return root_tasks
    
    def _build_task_clusters(self, root_tasks: List[str]) -> Dict[str, Set[str]]:
        """Build clusters of related tasks starting from roots"""
        clusters = {}
        visited = set()
        
        # Create clusters from each root task
        for root_id in root_tasks:
            if root_id in visited:
                continue
                
            cluster_id = f"cluster_{root_id}"
            cluster_tasks = set()
            
            # Recursively collect all children and dependencies
            self._collect_related_tasks(root_id, cluster_tasks, visited)
            
            if cluster_tasks:
                clusters[cluster_id] = cluster_tasks
        
        # Handle any remaining unvisited tasks (cycles, disconnected)
        all_regular_tasks = {task_id for task_id in self.tasks.keys() 
                            if not task_id.startswith(('phase_', 'root_'))}
        unvisited = all_regular_tasks - visited
        
        if unvisited:
            logger.info(f"   Found {len(unvisited)} disconnected tasks, creating separate clusters")
            
            # Group disconnected tasks by their relationships
            unvisited_copy = unvisited.copy()
            for task_id in unvisited_copy:
                if task_id in visited:
                    continue
                    
                cluster_id = f"cluster_disconnected_{task_id}"
                cluster_tasks = set()
                
                self._collect_related_tasks(task_id, cluster_tasks, visited)
                
                if cluster_tasks:
                    clusters[cluster_id] = cluster_tasks
        
        # Final check - ensure ALL tasks are in some cluster
        final_unvisited = all_regular_tasks - visited
        if final_unvisited:
            logger.warning(f"   Still have {len(final_unvisited)} unvisited tasks after clustering")
            # Put them in a general cluster
            clusters['cluster_uncategorized'] = final_unvisited
            visited.update(final_unvisited)
        
        logger.info(f"   Created {len(clusters)} task clusters covering {len(visited)} tasks")
        
        return clusters
    
    def _collect_related_tasks(self, task_id: str, cluster: Set[str], visited: Set[str], 
                              unvisited: Set[str] = None):
        """Recursively collect all tasks related to the given task"""
        if task_id in visited or task_id.startswith(('phase_', 'root_')):
            return
            
        visited.add(task_id)
        cluster.add(task_id)
        
        if unvisited and task_id in unvisited:
            unvisited.remove(task_id)
        
        # Add all children
        for child_id in self.children_map.get(task_id, []):
            self._collect_related_tasks(child_id, cluster, visited, unvisited)
        
        # Add all dependencies (tasks this depends on should be in same cluster)
        for dep_id in self.dependency_map.get(task_id, []):
            self._collect_related_tasks(dep_id, cluster, visited, unvisited)
        
        # Add all dependents (tasks that depend on this)
        for other_id, deps in self.dependency_map.items():
            if task_id in deps and other_id not in visited:
                self._collect_related_tasks(other_id, cluster, visited, unvisited)
    
    def _analyze_clusters(self, clusters: Dict[str, Set[str]]) -> Dict[str, Any]:
        """Analyze characteristics of each cluster"""
        cluster_analysis = {}
        
        for cluster_id, task_ids in clusters.items():
            # Get all tasks in cluster
            cluster_tasks = [self.tasks[tid] for tid in task_ids]
            
            # Analyze content to determine workstream type
            workstream_type = self._determine_workstream_type(cluster_tasks)
            
            # Find the most senior task (root of hierarchy)
            root_task = self._find_cluster_root(task_ids)
            
            # Analyze task statuses
            status_counts = defaultdict(int)
            for task in cluster_tasks:
                status_counts[task.get('status', 'unknown')] += 1
            
            cluster_analysis[cluster_id] = {
                'size': len(task_ids),
                'workstream_type': workstream_type,
                'root_task': root_task,
                'status_distribution': dict(status_counts),
                'has_active_work': status_counts.get('in_progress', 0) > 0,
                'completion_rate': status_counts.get('completed', 0) / len(task_ids) if task_ids else 0
            }
        
        return cluster_analysis
    
    def _determine_workstream_type(self, tasks: List[Dict[str, Any]]) -> str:
        """Determine the workstream type based on task content"""
        # Aggregate all text from tasks
        all_text = ""
        for task in tasks:
            all_text += f" {task.get('title', '')} {task.get('description', '')}"
        all_text = all_text.lower()
        
        # Score each workstream type
        workstream_scores = defaultdict(int)
        
        patterns = {
            'authentication': ['auth', 'login', 'user', 'profile', 'session', 'signup'],
            'quote_calculator': ['quote', 'calculator', 'pricing', 'estimate'],
            'dashboard': ['dashboard', 'admin', 'management', 'overview'],
            'api_development': ['api', 'endpoint', 'service', 'backend'],
            'database': ['database', 'schema', 'table', 'migration'],
            'ui_development': ['ui', 'component', 'page', 'interface', 'frontend'],
            'testing': ['test', 'testing', 'quality', 'qa'],
            'deployment': ['deploy', 'deployment', 'production', 'ci', 'cd']
        }
        
        for ws_type, keywords in patterns.items():
            for keyword in keywords:
                if keyword in all_text:
                    workstream_scores[ws_type] += all_text.count(keyword)
        
        # Return the highest scoring type, or 'general' if no clear match
        if workstream_scores:
            return max(workstream_scores.items(), key=lambda x: x[1])[0]
        return 'general'
    
    def _find_cluster_root(self, task_ids: Set[str]) -> str:
        """Find the root task of a cluster (most senior in hierarchy)"""
        # Find tasks with no parent within the cluster
        cluster_roots = []
        
        for task_id in task_ids:
            parent_id = self.parent_map.get(task_id)
            if not parent_id or parent_id not in task_ids:
                cluster_roots.append(task_id)
        
        # If multiple roots, pick the oldest (by ID) or largest (by children)
        if not cluster_roots:
            # Cycle detected, just pick one
            return sorted(task_ids)[0]
        elif len(cluster_roots) == 1:
            return cluster_roots[0]
        else:
            # Pick the one with most children in cluster
            return max(cluster_roots, 
                      key=lambda r: len(set(self.children_map.get(r, [])) & task_ids))


class RelationshipAwareMigration:
    """Performs migration while preserving task relationships"""
    
    def __init__(self, all_tasks: List[Dict[str, Any]], phase_mapping: Dict[str, Any]):
        self.all_tasks = all_tasks
        self.phase_mapping = phase_mapping
        self.analyzer = TaskRelationshipAnalyzer(all_tasks)
        
    async def create_workstream_structure(self) -> Dict[str, Any]:
        """Create workstream structure based on relationship analysis"""
        logger.info("🏗️ Building relationship-aware workstream structure...")
        
        # Analyze relationships
        analysis = self.analyzer.analyze_relationships()
        clusters = analysis['clusters']
        cluster_analysis = analysis['cluster_analysis']
        
        # Group clusters by phase based on their characteristics
        phase_clusters = self._assign_clusters_to_phases(clusters, cluster_analysis)
        
        # Create workstream mappings
        workstream_mappings = {}
        task_assignments = {}
        
        for phase_id, phase_cluster_map in phase_clusters.items():
            # Consolidate small clusters within each phase
            consolidated = self._consolidate_clusters(phase_cluster_map, cluster_analysis)
            
            # Create workstreams from consolidated clusters
            for ws_key, cluster_data in consolidated.items():
                workstream_id = f"root_{phase_id}_{ws_key}"
                
                # Get all tasks in this workstream
                all_cluster_tasks = []
                for cluster_id in cluster_data['clusters']:
                    all_cluster_tasks.extend(clusters[cluster_id])
                
                # Create workstream mapping
                workstream_mappings[workstream_id] = {
                    'phase_id': phase_id,
                    'workstream_key': ws_key,
                    'tasks': [self.analyzer.tasks[tid] for tid in all_cluster_tasks],
                    'title': self._get_workstream_title(ws_key),
                    'preserve_hierarchy': True
                }
                
                # Assign tasks to workstream
                for task_id in all_cluster_tasks:
                    task_assignments[task_id] = workstream_id
        
        # Ensure NO task is left behind
        all_task_ids = {t['task_id'] for t in self.all_tasks 
                       if not t['task_id'].startswith(('phase_', 'root_'))}
        assigned_ids = set(task_assignments.keys())
        
        if all_task_ids != assigned_ids:
            logger.error(f"⚠️ Found {len(all_task_ids - assigned_ids)} unassigned tasks!")
            # This should never happen with our logic
        
        return {
            'workstream_mappings': workstream_mappings,
            'task_assignments': task_assignments,
            'relationship_stats': analysis['relationship_stats']
        }
    
    def _assign_clusters_to_phases(self, clusters: Dict[str, Set[str]], 
                                  cluster_analysis: Dict[str, Any]) -> Dict[str, Dict]:
        """Assign clusters to appropriate phases"""
        phase_clusters = defaultdict(dict)
        
        for cluster_id, task_ids in clusters.items():
            analysis = cluster_analysis[cluster_id]
            
            # Determine phase based on cluster status
            if analysis['completion_rate'] == 1.0:
                # All completed -> Foundation
                phase = 'phase_1_foundation'
            elif analysis['has_active_work']:
                # Has active work -> Current phase
                phase = self.phase_mapping.get('current_phase', 'phase_2_intelligence')
            elif analysis['completion_rate'] > 0:
                # Some completed -> Current phase
                phase = self.phase_mapping.get('current_phase', 'phase_2_intelligence')
            else:
                # All pending -> Future phase
                phase = self.phase_mapping.get('next_phase', 'phase_3_coordination')
            
            ws_type = analysis['workstream_type']
            if ws_type not in phase_clusters[phase]:
                phase_clusters[phase][ws_type] = {
                    'clusters': [],
                    'total_tasks': 0
                }
            
            phase_clusters[phase][ws_type]['clusters'].append(cluster_id)
            phase_clusters[phase][ws_type]['total_tasks'] += analysis['size']
        
        return phase_clusters
    
    def _consolidate_clusters(self, phase_cluster_map: Dict[str, Dict], 
                            cluster_analysis: Dict[str, Any]) -> Dict[str, Dict]:
        """Consolidate small clusters to avoid too many workstreams"""
        consolidated = {}
        
        # First pass: Keep large workstreams
        small_clusters = []
        
        for ws_type, cluster_data in phase_cluster_map.items():
            if cluster_data['total_tasks'] >= 5:  # Minimum size for standalone workstream
                consolidated[ws_type] = cluster_data
            else:
                small_clusters.append((ws_type, cluster_data))
        
        # Second pass: Merge small clusters
        if small_clusters:
            # Group small clusters into general
            general_clusters = []
            general_tasks = 0
            
            for ws_type, cluster_data in small_clusters:
                general_clusters.extend(cluster_data['clusters'])
                general_tasks += cluster_data['total_tasks']
            
            if general_clusters:
                consolidated['general'] = {
                    'clusters': general_clusters,
                    'total_tasks': general_tasks
                }
        
        # Ensure we don't exceed maximum workstreams
        if len(consolidated) > 7:
            # Merge smallest workstreams into general
            sorted_ws = sorted(consolidated.items(), 
                             key=lambda x: x[1]['total_tasks'], 
                             reverse=True)
            
            keep = dict(sorted_ws[:6])
            merge = sorted_ws[6:]
            
            general_clusters = keep.get('general', {}).get('clusters', [])
            general_tasks = keep.get('general', {}).get('total_tasks', 0)
            
            for ws_type, cluster_data in merge:
                if ws_type != 'general':
                    general_clusters.extend(cluster_data['clusters'])
                    general_tasks += cluster_data['total_tasks']
            
            keep['general'] = {
                'clusters': general_clusters,
                'total_tasks': general_tasks
            }
            
            consolidated = keep
        
        return consolidated
    
    def _get_workstream_title(self, ws_key: str) -> str:
        """Get human-readable workstream title"""
        titles = {
            'authentication': 'Authentication & User Management',
            'quote_calculator': 'Quote Calculator System',
            'dashboard': 'Dashboard Features',
            'api_development': 'API Development',
            'database': 'Database Architecture',
            'ui_development': 'UI Components & Pages',
            'testing': 'Testing Framework',
            'deployment': 'Deployment & DevOps',
            'general': 'General Tasks'
        }
        return titles.get(ws_key, ws_key.replace('_', ' ').title())