# Agent-MCP Agent Learning and Adaptation System
"""
Advanced agent learning system with adaptation, specialization training,
collaboration protocols, and performance optimization.
"""

import asyncio
import json
import time
import sqlite3
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import hashlib
import numpy as np

# Local imports
from ...core.config import logger
from ...db.connection import get_db_connection
from ...external.openai_service import get_openai_client
from ...core import globals as g


class LearningType(Enum):
    """Types of learning for agents."""
    SUPERVISED = "supervised"
    REINFORCEMENT = "reinforcement"
    UNSUPERVISED = "unsupervised"
    TRANSFER = "transfer"
    META = "meta"


class SpecializationType(Enum):
    """Types of agent specializations."""
    CODE_REVIEW = "code_review"
    DEBUGGING = "debugging"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    ARCHITECTURE = "architecture"
    SECURITY = "security"
    PERFORMANCE = "performance"
    UI_UX = "ui_ux"
    DATA_ANALYSIS = "data_analysis"
    GENERAL = "general"


class CollaborationProtocol(Enum):
    """Types of collaboration protocols."""
    HIERARCHICAL = "hierarchical"
    PEER_TO_PEER = "peer_to_peer"
    SWARM = "swarm"
    MASTER_WORKER = "master_worker"
    CONSENSUS = "consensus"


@dataclass
class LearningExperience:
    """Represents a learning experience for an agent."""
    experience_id: str
    agent_id: str
    task_type: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    feedback_score: float
    learning_type: LearningType
    specialization: Optional[SpecializationType] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AgentSpecialization:
    """Represents an agent's specialization profile."""
    agent_id: str
    specialization_type: SpecializationType
    proficiency_level: float  # 0.0 to 1.0
    experience_count: int = 0
    success_rate: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)
    training_data: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class CollaborationSession:
    """Represents a collaboration session between agents."""
    session_id: str
    protocol: CollaborationProtocol
    participants: List[str]
    task_description: str
    roles: Dict[str, str]  # agent_id -> role
    status: str = "active"  # active, completed, failed
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    outcomes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Performance metrics for agent learning and adaptation."""
    agent_id: str
    task_completion_rate: float = 0.0
    average_response_time: float = 0.0
    learning_progress: float = 0.0
    specialization_proficiency: Dict[str, float] = field(default_factory=dict)
    collaboration_success_rate: float = 0.0
    adaptation_score: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)


class AgentLearningSystem:
    """Advanced agent learning and adaptation system."""
    
    def __init__(self):
        self.learning_experiences: Dict[str, LearningExperience] = {}
        self.specializations: Dict[str, AgentSpecialization] = {}
        self.collaboration_sessions: Dict[str, CollaborationSession] = {}
        self.performance_metrics: Dict[str, PerformanceMetrics] = {}
        self.adaptation_rules: Dict[str, Any] = {}
        
    async def record_learning_experience(
        self,
        agent_id: str,
        task_type: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        feedback_score: float,
        learning_type: LearningType = LearningType.SUPERVISED,
        specialization: Optional[SpecializationType] = None
    ) -> str:
        """
        Record a learning experience for an agent.
        
        Args:
            agent_id: ID of the agent
            task_type: Type of task performed
            input_data: Input data for the task
            output_data: Output data from the task
            feedback_score: Feedback score (0.0 to 1.0)
            learning_type: Type of learning
            specialization: Optional specialization type
            
        Returns:
            Experience ID
        """
        experience_id = f"exp_{hashlib.md5(f'{agent_id}_{time.time()}'.encode()).hexdigest()[:8]}"
        
        experience = LearningExperience(
            experience_id=experience_id,
            agent_id=agent_id,
            task_type=task_type,
            input_data=input_data,
            output_data=output_data,
            feedback_score=feedback_score,
            learning_type=learning_type,
            specialization=specialization
        )
        
        self.learning_experiences[experience_id] = experience
        
        # Update agent performance metrics
        await self._update_agent_performance(agent_id, experience)
        
        # Store in database
        await self._store_learning_experience(experience)
        
        logger.info(f"Recorded learning experience {experience_id} for agent {agent_id}")
        return experience_id
    
    async def _update_agent_performance(self, agent_id: str, experience: LearningExperience) -> None:
        """Update agent performance metrics based on learning experience."""
        if agent_id not in self.performance_metrics:
            self.performance_metrics[agent_id] = PerformanceMetrics(agent_id=agent_id)
        
        metrics = self.performance_metrics[agent_id]
        
        # Update learning progress
        recent_experiences = [
            exp for exp in self.learning_experiences.values()
            if exp.agent_id == agent_id and 
            exp.timestamp > datetime.now() - timedelta(days=7)
        ]
        
        if recent_experiences:
            avg_feedback = np.mean([exp.feedback_score for exp in recent_experiences])
            metrics.learning_progress = avg_feedback
            metrics.task_completion_rate = len([exp for exp in recent_experiences if exp.feedback_score > 0.7]) / len(recent_experiences)
        
        # Update specialization proficiency
        if experience.specialization:
            spec_key = experience.specialization.value
            if spec_key not in metrics.specialization_proficiency:
                metrics.specialization_proficiency[spec_key] = 0.0
            
            # Update specialization proficiency based on feedback
            current_prof = metrics.specialization_proficiency[spec_key]
            new_prof = (current_prof + experience.feedback_score) / 2
            metrics.specialization_proficiency[spec_key] = min(1.0, new_prof)
        
        metrics.last_updated = datetime.now()
    
    async def _store_learning_experience(self, experience: LearningExperience) -> None:
        """Store learning experience in database."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO agent_learning_experiences (
                    experience_id, agent_id, task_type, input_data, output_data,
                    feedback_score, learning_type, specialization, metadata, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                experience.experience_id,
                experience.agent_id,
                experience.task_type,
                json.dumps(experience.input_data),
                json.dumps(experience.output_data),
                experience.feedback_score,
                experience.learning_type.value,
                experience.specialization.value if experience.specialization else None,
                json.dumps(experience.metadata),
                experience.timestamp.isoformat()
            ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error storing learning experience: {e}")
        finally:
            conn.close()
    
    async def train_specialization(
        self,
        agent_id: str,
        specialization_type: SpecializationType,
        training_data: List[Dict[str, Any]]
    ) -> bool:
        """
        Train an agent for a specific specialization.
        
        Args:
            agent_id: ID of the agent to train
            specialization_type: Type of specialization to train
            training_data: Training data for the specialization
            
        Returns:
            Success status
        """
        try:
            # Create or update specialization profile
            spec_key = f"{agent_id}_{specialization_type.value}"
            
            if spec_key not in self.specializations:
                self.specializations[spec_key] = AgentSpecialization(
                    agent_id=agent_id,
                    specialization_type=specialization_type,
                    proficiency_level=0.0
                )
            
            specialization = self.specializations[spec_key]
            
            # Process training data
            success_count = 0
            total_experiences = 0
            
            for training_item in training_data:
                # Simulate training experience
                feedback_score = training_item.get("feedback_score", 0.8)
                
                await self.record_learning_experience(
                    agent_id=agent_id,
                    task_type=training_item.get("task_type", "training"),
                    input_data=training_item.get("input_data", {}),
                    output_data=training_item.get("output_data", {}),
                    feedback_score=feedback_score,
                    learning_type=LearningType.SUPERVISED,
                    specialization=specialization_type
                )
                
                total_experiences += 1
                if feedback_score > 0.7:
                    success_count += 1
            
            # Update specialization metrics
            specialization.experience_count += total_experiences
            specialization.success_rate = success_count / total_experiences if total_experiences > 0 else 0.0
            specialization.proficiency_level = min(1.0, specialization.proficiency_level + (specialization.success_rate * 0.1))
            specialization.last_updated = datetime.now()
            specialization.training_data.extend(training_data)
            
            # Store in database
            await self._store_specialization(specialization)
            
            logger.info(f"Trained agent {agent_id} for {specialization_type.value} specialization")
            return True
            
        except Exception as e:
            logger.error(f"Error training specialization: {e}")
            return False
    
    async def _store_specialization(self, specialization: AgentSpecialization) -> None:
        """Store specialization in database."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO agent_specializations (
                    agent_id, specialization_type, proficiency_level, experience_count,
                    success_rate, last_updated, training_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                specialization.agent_id,
                specialization.specialization_type.value,
                specialization.proficiency_level,
                specialization.experience_count,
                specialization.success_rate,
                specialization.last_updated.isoformat(),
                json.dumps(specialization.training_data)
            ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error storing specialization: {e}")
        finally:
            conn.close()
    
    async def create_collaboration_session(
        self,
        protocol: CollaborationProtocol,
        participants: List[str],
        task_description: str,
        roles: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Create a collaboration session between agents.
        
        Args:
            protocol: Collaboration protocol to use
            participants: List of agent IDs participating
            task_description: Description of the collaborative task
            roles: Optional role assignments for participants
            
        Returns:
            Session ID
        """
        session_id = f"collab_{hashlib.md5(f'{protocol.value}_{time.time()}'.encode()).hexdigest()[:8]}"
        
        if roles is None:
            roles = self._assign_default_roles(participants, protocol)
        
        session = CollaborationSession(
            session_id=session_id,
            protocol=protocol,
            participants=participants,
            task_description=task_description,
            roles=roles
        )
        
        self.collaboration_sessions[session_id] = session
        
        # Store in database
        await self._store_collaboration_session(session)
        
        logger.info(f"Created collaboration session {session_id} with protocol {protocol.value}")
        return session_id
    
    def _assign_default_roles(self, participants: List[str], protocol: CollaborationProtocol) -> Dict[str, str]:
        """Assign default roles based on protocol."""
        roles = {}
        
        if protocol == CollaborationProtocol.HIERARCHICAL:
            roles[participants[0]] = "coordinator"
            for participant in participants[1:]:
                roles[participant] = "worker"
                
        elif protocol == CollaborationProtocol.MASTER_WORKER:
            roles[participants[0]] = "master"
            for participant in participants[1:]:
                roles[participant] = "worker"
                
        elif protocol == CollaborationProtocol.PEER_TO_PEER:
            for participant in participants:
                roles[participant] = "peer"
                
        elif protocol == CollaborationProtocol.SWARM:
            for participant in participants:
                roles[participant] = "swarm_member"
                
        elif protocol == CollaborationProtocol.CONSENSUS:
            for participant in participants:
                roles[participant] = "consensus_member"
        
        return roles
    
    async def _store_collaboration_session(self, session: CollaborationSession) -> None:
        """Store collaboration session in database."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO agent_collaboration_sessions (
                    session_id, protocol, participants, task_description, roles,
                    status, start_time, end_time, outcomes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session.session_id,
                session.protocol.value,
                json.dumps(session.participants),
                session.task_description,
                json.dumps(session.roles),
                session.status,
                session.start_time.isoformat(),
                session.end_time.isoformat() if session.end_time else None,
                json.dumps(session.outcomes)
            ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error storing collaboration session: {e}")
        finally:
            conn.close()
    
    async def execute_collaboration_protocol(
        self,
        session_id: str,
        task_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a collaboration protocol for a session.
        
        Args:
            session_id: ID of the collaboration session
            task_data: Data for the collaborative task
            
        Returns:
            Results of the collaboration
        """
        if session_id not in self.collaboration_sessions:
            raise ValueError(f"Collaboration session {session_id} not found")
        
        session = self.collaboration_sessions[session_id]
        
        try:
            if session.protocol == CollaborationProtocol.HIERARCHICAL:
                return await self._execute_hierarchical_protocol(session, task_data)
            elif session.protocol == CollaborationProtocol.PEER_TO_PEER:
                return await self._execute_peer_to_peer_protocol(session, task_data)
            elif session.protocol == CollaborationProtocol.SWARM:
                return await self._execute_swarm_protocol(session, task_data)
            elif session.protocol == CollaborationProtocol.MASTER_WORKER:
                return await self._execute_master_worker_protocol(session, task_data)
            elif session.protocol == CollaborationProtocol.CONSENSUS:
                return await self._execute_consensus_protocol(session, task_data)
            else:
                raise ValueError(f"Unknown collaboration protocol: {session.protocol}")
                
        except Exception as e:
            logger.error(f"Error executing collaboration protocol: {e}")
            session.status = "failed"
            session.outcomes["error"] = str(e)
            return {"error": str(e)}
    
    async def _execute_hierarchical_protocol(
        self,
        session: CollaborationSession,
        task_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute hierarchical collaboration protocol."""
        coordinator_id = None
        workers = []
        
        for agent_id, role in session.roles.items():
            if role == "coordinator":
                coordinator_id = agent_id
            else:
                workers.append(agent_id)
        
        if not coordinator_id:
            raise ValueError("No coordinator found in hierarchical session")
        
        # Coordinator distributes tasks to workers
        subtasks = self._divide_task_for_workers(task_data, len(workers))
        
        # Execute subtasks in parallel
        worker_results = []
        for i, worker_id in enumerate(workers):
            result = await self._execute_agent_task(worker_id, subtasks[i])
            worker_results.append(result)
        
        # Coordinator synthesizes results
        final_result = await self._synthesize_worker_results(coordinator_id, worker_results)
        
        session.status = "completed"
        session.end_time = datetime.now()
        session.outcomes = final_result
        
        return final_result
    
    async def _execute_peer_to_peer_protocol(
        self,
        session: CollaborationSession,
        task_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute peer-to-peer collaboration protocol."""
        # Each peer works on the same task independently
        peer_results = []
        
        for agent_id in session.participants:
            result = await self._execute_agent_task(agent_id, task_data)
            peer_results.append(result)
        
        # Combine peer results using voting or averaging
        combined_result = self._combine_peer_results(peer_results)
        
        session.status = "completed"
        session.end_time = datetime.now()
        session.outcomes = combined_result
        
        return combined_result
    
    async def _execute_swarm_protocol(
        self,
        session: CollaborationSession,
        task_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute swarm collaboration protocol."""
        # Swarm members work on different aspects simultaneously
        swarm_tasks = self._create_swarm_tasks(task_data, len(session.participants))
        
        swarm_results = []
        for i, agent_id in enumerate(session.participants):
            result = await self._execute_agent_task(agent_id, swarm_tasks[i])
            swarm_results.append(result)
        
        # Emergent behavior: combine results based on swarm intelligence
        emergent_result = self._create_emergent_behavior(swarm_results)
        
        session.status = "completed"
        session.end_time = datetime.now()
        session.outcomes = emergent_result
        
        return emergent_result
    
    async def _execute_master_worker_protocol(
        self,
        session: CollaborationSession,
        task_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute master-worker collaboration protocol."""
        master_id = None
        workers = []
        
        for agent_id, role in session.roles.items():
            if role == "master":
                master_id = agent_id
            else:
                workers.append(agent_id)
        
        if not master_id:
            raise ValueError("No master found in master-worker session")
        
        # Master coordinates and workers execute
        worker_tasks = self._create_worker_tasks(task_data, len(workers))
        
        worker_results = []
        for i, worker_id in enumerate(workers):
            result = await self._execute_agent_task(worker_id, worker_tasks[i])
            worker_results.append(result)
        
        # Master finalizes the result
        final_result = await self._finalize_master_worker_result(master_id, worker_results)
        
        session.status = "completed"
        session.end_time = datetime.now()
        session.outcomes = final_result
        
        return final_result
    
    async def _execute_consensus_protocol(
        self,
        session: CollaborationSession,
        task_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute consensus collaboration protocol."""
        # All members work on the same task
        member_results = []
        
        for agent_id in session.participants:
            result = await self._execute_agent_task(agent_id, task_data)
            member_results.append(result)
        
        # Reach consensus through voting or discussion
        consensus_result = self._reach_consensus(member_results)
        
        session.status = "completed"
        session.end_time = datetime.now()
        session.outcomes = consensus_result
        
        return consensus_result
    
    def _divide_task_for_workers(self, task_data: Dict[str, Any], num_workers: int) -> List[Dict[str, Any]]:
        """Divide a task into subtasks for workers."""
        # Simple division - could be enhanced with intelligent task decomposition
        subtasks = []
        task_keys = list(task_data.keys())
        
        for i in range(num_workers):
            start_idx = (i * len(task_keys)) // num_workers
            end_idx = ((i + 1) * len(task_keys)) // num_workers
            
            subtask = {key: task_data[key] for key in task_keys[start_idx:end_idx]}
            subtasks.append(subtask)
        
        return subtasks
    
    async def _execute_agent_task(self, agent_id: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task for a specific agent."""
        # Simulate agent task execution
        # In a real implementation, this would communicate with the actual agent
        
        # For now, return a simulated result
        return {
            "agent_id": agent_id,
            "task_result": f"Simulated result for {agent_id}",
            "confidence": 0.8,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _synthesize_worker_results(self, coordinator_id: str, worker_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Synthesize results from workers."""
        # Simulate result synthesis
        return {
            "coordinator_id": coordinator_id,
            "synthesized_result": "Combined result from workers",
            "worker_count": len(worker_results),
            "confidence": 0.9
        }
    
    def _combine_peer_results(self, peer_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine results from peer agents."""
        # Simple averaging of confidence scores
        avg_confidence = np.mean([result.get("confidence", 0.5) for result in peer_results])
        
        return {
            "combined_result": "Averaged peer results",
            "peer_count": len(peer_results),
            "average_confidence": avg_confidence
        }
    
    def _create_swarm_tasks(self, task_data: Dict[str, Any], num_members: int) -> List[Dict[str, Any]]:
        """Create specialized tasks for swarm members."""
        # Create different perspectives on the same task
        swarm_tasks = []
        
        for i in range(num_members):
            task = {
                "perspective": f"perspective_{i}",
                "focus_area": f"area_{i}",
                "data": task_data
            }
            swarm_tasks.append(task)
        
        return swarm_tasks
    
    def _create_emergent_behavior(self, swarm_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create emergent behavior from swarm results."""
        # Combine swarm results to create emergent behavior
        return {
            "emergent_behavior": "Combined swarm intelligence",
            "member_count": len(swarm_results),
            "complexity_level": "high"
        }
    
    def _create_worker_tasks(self, task_data: Dict[str, Any], num_workers: int) -> List[Dict[str, Any]]:
        """Create specialized tasks for workers."""
        # Similar to swarm tasks but more structured
        worker_tasks = []
        
        for i in range(num_workers):
            task = {
                "worker_id": i,
                "specialization": f"specialization_{i}",
                "data": task_data
            }
            worker_tasks.append(task)
        
        return worker_tasks
    
    async def _finalize_master_worker_result(self, master_id: str, worker_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Finalize result from master-worker collaboration."""
        return {
            "master_id": master_id,
            "finalized_result": "Master-finalized result",
            "worker_count": len(worker_results),
            "quality_score": 0.95
        }
    
    def _reach_consensus(self, member_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Reach consensus among member results."""
        # Simple voting mechanism
        votes = {}
        for result in member_results:
            key = result.get("task_result", "unknown")
            votes[key] = votes.get(key, 0) + 1
        
        # Find most common result
        consensus_result = max(votes.items(), key=lambda x: x[1])[0]
        
        return {
            "consensus_result": consensus_result,
            "member_count": len(member_results),
            "agreement_level": max(votes.values()) / len(member_results)
        }
    
    async def optimize_agent_performance(self, agent_id: str) -> Dict[str, Any]:
        """
        Optimize agent performance based on learning data.
        
        Args:
            agent_id: ID of the agent to optimize
            
        Returns:
            Optimization results
        """
        try:
            # Analyze agent's learning history
            agent_experiences = [
                exp for exp in self.learning_experiences.values()
                if exp.agent_id == agent_id
            ]
            
            if not agent_experiences:
                return {"error": "No learning experiences found for agent"}
            
            # Calculate optimization metrics
            recent_experiences = [
                exp for exp in agent_experiences
                if exp.timestamp > datetime.now() - timedelta(days=30)
            ]
            
            optimization_results = {
                "agent_id": agent_id,
                "total_experiences": len(agent_experiences),
                "recent_experiences": len(recent_experiences),
                "average_feedback": np.mean([exp.feedback_score for exp in recent_experiences]),
                "learning_trend": self._calculate_learning_trend(recent_experiences),
                "specialization_recommendations": self._generate_specialization_recommendations(agent_id),
                "collaboration_recommendations": self._generate_collaboration_recommendations(agent_id),
                "performance_improvements": self._suggest_performance_improvements(agent_id)
            }
            
            # Apply optimizations
            await self._apply_optimizations(agent_id, optimization_results)
            
            return optimization_results
            
        except Exception as e:
            logger.error(f"Error optimizing agent performance: {e}")
            return {"error": str(e)}
    
    def _calculate_learning_trend(self, experiences: List[LearningExperience]) -> str:
        """Calculate learning trend from experiences."""
        if len(experiences) < 2:
            return "insufficient_data"
        
        # Calculate trend based on feedback scores over time
        sorted_experiences = sorted(experiences, key=lambda x: x.timestamp)
        scores = [exp.feedback_score for exp in sorted_experiences]
        
        if len(scores) >= 2:
            trend = np.polyfit(range(len(scores)), scores, 1)[0]
            if trend > 0.01:
                return "improving"
            elif trend < -0.01:
                return "declining"
            else:
                return "stable"
        
        return "unknown"
    
    def _generate_specialization_recommendations(self, agent_id: str) -> List[str]:
        """Generate specialization recommendations for an agent."""
        recommendations = []
        
        # Analyze agent's current specializations
        agent_specs = [
            spec for spec in self.specializations.values()
            if spec.agent_id == agent_id
        ]
        
        # Recommend new specializations based on performance
        if agent_specs:
            avg_proficiency = np.mean([spec.proficiency_level for spec in agent_specs])
            
            if avg_proficiency > 0.8:
                recommendations.append("Consider advanced specializations")
            elif avg_proficiency < 0.5:
                recommendations.append("Focus on core specializations first")
        
        # Recommend based on task types
        agent_experiences = [
            exp for exp in self.learning_experiences.values()
            if exp.agent_id == agent_id
        ]
        
        task_types = [exp.task_type for exp in agent_experiences]
        if "code_review" in task_types and "debugging" not in task_types:
            recommendations.append("Consider debugging specialization")
        
        return recommendations
    
    def _generate_collaboration_recommendations(self, agent_id: str) -> List[str]:
        """Generate collaboration recommendations for an agent."""
        recommendations = []
        
        # Analyze collaboration history
        agent_sessions = [
            session for session in self.collaboration_sessions.values()
            if agent_id in session.participants
        ]
        
        if not agent_sessions:
            recommendations.append("Start with simple peer-to-peer collaborations")
        else:
            successful_sessions = [s for s in agent_sessions if s.status == "completed"]
            success_rate = len(successful_sessions) / len(agent_sessions) if agent_sessions else 0
            
            if success_rate > 0.8:
                recommendations.append("Ready for complex hierarchical collaborations")
            elif success_rate < 0.5:
                recommendations.append("Focus on improving basic collaboration skills")
        
        return recommendations
    
    def _suggest_performance_improvements(self, agent_id: str) -> List[str]:
        """Suggest performance improvements for an agent."""
        improvements = []
        
        # Analyze recent performance
        recent_experiences = [
            exp for exp in self.learning_experiences.values()
            if exp.agent_id == agent_id and
            exp.timestamp > datetime.now() - timedelta(days=7)
        ]
        
        if recent_experiences:
            avg_feedback = np.mean([exp.feedback_score for exp in recent_experiences])
            
            if avg_feedback < 0.6:
                improvements.append("Focus on quality over speed")
            elif avg_feedback > 0.9:
                improvements.append("Consider taking on more complex tasks")
            
            # Analyze task types for improvement areas
            task_types = [exp.task_type for exp in recent_experiences]
            if "code_review" in task_types:
                improvements.append("Consider specializing in code review")
        
        return improvements
    
    async def _apply_optimizations(self, agent_id: str, optimization_results: Dict[str, Any]) -> None:
        """Apply optimizations to agent performance."""
        # Update agent's learning parameters based on optimization results
        if agent_id in self.performance_metrics:
            metrics = self.performance_metrics[agent_id]
            
            # Update adaptation score based on learning trend
            learning_trend = optimization_results.get("learning_trend", "stable")
            if learning_trend == "improving":
                metrics.adaptation_score = min(1.0, metrics.adaptation_score + 0.1)
            elif learning_trend == "declining":
                metrics.adaptation_score = max(0.0, metrics.adaptation_score - 0.1)
            
            metrics.last_updated = datetime.now()
        
        # Store optimization results
        await self._store_optimization_results(agent_id, optimization_results)
    
    async def _store_optimization_results(self, agent_id: str, results: Dict[str, Any]) -> None:
        """Store optimization results in database."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO agent_optimization_results (
                    agent_id, results, timestamp
                ) VALUES (?, ?, ?)
            """, (
                agent_id,
                json.dumps(results),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error storing optimization results: {e}")
        finally:
            conn.close()
    
    def get_agent_learning_summary(self, agent_id: str) -> Dict[str, Any]:
        """Get a summary of agent's learning progress."""
        agent_experiences = [
            exp for exp in self.learning_experiences.values()
            if exp.agent_id == agent_id
        ]
        
        agent_specs = [
            spec for spec in self.specializations.values()
            if spec.agent_id == agent_id
        ]
        
        agent_sessions = [
            session for session in self.collaboration_sessions.values()
            if agent_id in session.participants
        ]
        
        return {
            "agent_id": agent_id,
            "total_experiences": len(agent_experiences),
            "specializations": len(agent_specs),
            "collaboration_sessions": len(agent_sessions),
            "average_feedback": np.mean([exp.feedback_score for exp in agent_experiences]) if agent_experiences else 0.0,
            "specialization_proficiencies": {
                spec.specialization_type.value: spec.proficiency_level
                for spec in agent_specs
            },
            "collaboration_success_rate": len([s for s in agent_sessions if s.status == "completed"]) / len(agent_sessions) if agent_sessions else 0.0
        }


# Global instance
agent_learning_system = AgentLearningSystem()
