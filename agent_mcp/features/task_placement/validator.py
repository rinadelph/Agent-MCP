# Task placement validator using RAG system
import json
from typing import Optional, List, Dict, Any
from ...tools.rag_tools import ask_project_rag_tool_impl
import mcp.types as mcp_types
from ...core.config import logger, TASK_ANALYSIS_MODEL, TASK_ANALYSIS_MAX_TOKENS

async def validate_task_placement(
    title: str,
    description: str,
    parent_task_id: Optional[str],
    depends_on_tasks: Optional[List[str]],
    created_by: str,
    auth_token: str
) -> Dict[str, Any]:
    """
    Validate task placement using RAG system.
    
    Args:
        title: Proposed task title
        description: Proposed task description
        parent_task_id: Proposed parent task ID (if any)
        depends_on_tasks: List of proposed dependency task IDs
        created_by: Agent ID creating the task
        auth_token: Authentication token for RAG query
        
    Returns:
        Dictionary with validation results:
        {
            "status": "approved" | "suggest_changes" | "warning" | "denied",
            "suggestions": {
                "parent_task": suggested_parent_task_id,
                "dependencies": [suggested_dep_ids],
                "reasoning": "Explanation for suggestions"
            },
            "duplicates": [{
                "task_id": existing_task_id,
                "similarity": 0.0-1.0,
                "title": existing_title
            }],
            "message": "Human-readable message"
        }
    """
    try:
        # Check if trying to create a root task (no parent)
        from ...db.connection import get_db_connection
        root_task_check = ""
        if parent_task_id is None:
            # Check if a root task already exists
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM tasks WHERE parent_task IS NULL")
            root_count = cursor.fetchone()['count']
            conn.close()
            
            if root_count > 0:
                root_task_check = f"""
                CRITICAL: There are already {root_count} root task(s) in the system. 
                ONLY ONE root task is allowed. This task MUST have a parent.
                """
        
        # Format the query for RAG with emphasis on critical thinking
        query = f"""
        {root_task_check}
        
        CRITICAL THINKING REQUIRED: Analyze the proposed task placement with deep consideration of the ENTIRE task hierarchy:
        
        Title: {title}
        Description: {description}
        Proposed Parent Task: {parent_task_id or 'None (ATTEMPTING TO CREATE ROOT TASK)'}
        Proposed Dependencies: {json.dumps(depends_on_tasks or [])}
        Created By: {created_by}
        
        YOU MUST CRITICALLY EVALUATE:
        
        1. HIERARCHY RULES:
           - There can be ONLY ONE root task (no parent) in the entire system
           - Every other task MUST have a parent
           - If proposing a root task, explain why this should be THE root task
        
        2. LOGICAL PLACEMENT:
           - Analyze ALL existing tasks to find the most logical parent
           - Consider the task's purpose, scope, and relationship to other tasks
           - Don't just accept the proposed parent - think if there's a better one
        
        3. DEPENDENCIES:
           - Identify ALL tasks this should depend on based on logical workflow
           - Consider both direct and indirect dependencies
           - Remove any redundant or incorrect dependencies
        
        4. DUPLICATION:
           - Check if similar tasks already exist
           - Consider if this should be a subtask of an existing task instead
        
        5. PROJECT STRUCTURE:
           - Ensure the task fits logically within the project's architecture
           - Consider the impact on the overall task hierarchy
        
        Please respond in the following JSON format:
        {{
            "placement_assessment": "appropriate" | "needs_adjustment" | "problematic",
            "hierarchy_analysis": {{
                "root_task_exists": true | false,
                "current_root_task_id": "task_id or null",
                "proposed_is_root": true | false,
                "hierarchy_violation": true | false
            }},
            "parent_suggestion": {{
                "recommended_parent": "task_id or null",
                "reasoning": "detailed explanation of why this parent is the most logical choice after analyzing all tasks"
            }},
            "dependency_suggestions": {{
                "add_dependencies": ["task_id1", "task_id2"],
                "remove_dependencies": ["task_id3"],
                "reasoning": "detailed explanation of the dependency logic"
            }},
            "duplication_check": {{
                "similar_tasks": [
                    {{
                        "task_id": "existing_task_id",
                        "title": "existing task title",
                        "similarity": 0.85,
                        "reasoning": "why they are similar"
                    }}
                ],
                "is_duplicate": true | false
            }},
            "critical_thinking_summary": "Your detailed analysis of how this task fits into the overall project structure",
            "overall_recommendation": "proceed" | "modify" | "reconsider" | "deny",
            "message": "Human-readable explanation of the assessment"
        }}
        """
        
        # For task analysis, use the cheaper model directly instead of the full RAG system
        # This allows us to use a different model for task placement analysis
        try:
            from ...features.rag.query import query_rag_system_with_model
        except ImportError:
            # If the function doesn't exist yet, fall back to regular RAG
            rag_response = await ask_project_rag_tool_impl({
                "token": auth_token,
                "query": query
            })
        else:
            # Use the cheaper model for task analysis
            response_text = await query_rag_system_with_model(
                query_text=query,
                model_name=TASK_ANALYSIS_MODEL,
                max_tokens=TASK_ANALYSIS_MAX_TOKENS
            )
            rag_response = [mcp_types.TextContent(type="text", text=response_text)]
        
        # Extract the text from the response
        response_text = rag_response[0].text if rag_response else ""
        
        # Check for "no knowledge" case
        if "no relevant context found" in response_text.lower() or "no knowledge" in response_text.lower():
            logger.info("RAG system has no task knowledge - recommending initial context setup")
            return {
                "status": "suggest_changes",
                "suggestions": {
                    "parent_task": None,  # Root level for initial task
                    "dependencies": [],
                    "reasoning": "No existing task hierarchy found. This should be a root-level task to establish the project structure."
                },
                "duplicates": [],
                "message": "No existing task knowledge found. Recommend creating as root task and adding project context/MCD."
            }
        
        # Try to parse JSON from the response
        try:
            # Look for JSON in the response (it might be wrapped in other text)
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                rag_data = json.loads(json_str)
            else:
                # Fallback if no JSON found
                rag_data = None
        except json.JSONDecodeError:
            logger.warning(f"Could not parse JSON from RAG response: {response_text[:200]}...")
            rag_data = None
        
        # Process the RAG response into our format
        if rag_data:
            # Check for hierarchy violations first
            hierarchy_analysis = rag_data.get("hierarchy_analysis", {})
            hierarchy_violation = hierarchy_analysis.get("hierarchy_violation", False)
            
            # Map RAG recommendations to our status codes
            status_map = {
                "proceed": "approved",
                "modify": "suggest_changes",
                "reconsider": "warning",
                "deny": "denied"
            }
            
            base_status = status_map.get(
                rag_data.get("overall_recommendation", "proceed"),
                "approved"
            )
            
            # Override status if hierarchy violation detected
            if hierarchy_violation and parent_task_id is None:
                status = "denied"
                logger.warning(f"Task creation denied due to hierarchy violation (attempting to create second root task)")
            else:
                status = base_status
            
            # Extract suggestions
            parent_suggestion = rag_data.get("parent_suggestion", {})
            dependency_suggestions = rag_data.get("dependency_suggestions", {})
            
            suggestions = {
                "parent_task": parent_suggestion.get("recommended_parent"),
                "dependencies": depends_on_tasks or []
            }
            
            # Apply dependency modifications
            if dependency_suggestions.get("add_dependencies"):
                suggestions["dependencies"].extend(
                    dependency_suggestions["add_dependencies"]
                )
            if dependency_suggestions.get("remove_dependencies"):
                suggestions["dependencies"] = [
                    d for d in suggestions["dependencies"]
                    if d not in dependency_suggestions["remove_dependencies"]
                ]
            
            # Remove duplicates and None values from dependencies
            suggestions["dependencies"] = list(filter(None, set(suggestions["dependencies"])))
            
            # Add reasoning
            reasoning_parts = []
            if parent_suggestion.get("reasoning"):
                reasoning_parts.append(f"Parent: {parent_suggestion['reasoning']}")
            if dependency_suggestions.get("reasoning"):
                reasoning_parts.append(f"Dependencies: {dependency_suggestions['reasoning']}")
            
            suggestions["reasoning"] = " | ".join(reasoning_parts) if reasoning_parts else None
            
            # Extract duplicate information
            duplication_info = rag_data.get("duplication_check", {})
            duplicates = []
            for similar_task in duplication_info.get("similar_tasks", []):
                duplicates.append({
                    "task_id": similar_task.get("task_id"),
                    "similarity": similar_task.get("similarity", 0.0),
                    "title": similar_task.get("title", "Unknown")
                })
            
            # Include critical thinking summary in message
            critical_thinking = rag_data.get("critical_thinking_summary", "")
            base_message = rag_data.get("message", "Task placement validated via RAG")
            full_message = f"{base_message}\n\nCritical Analysis: {critical_thinking}" if critical_thinking else base_message
            
            return {
                "status": status,
                "suggestions": suggestions,
                "duplicates": duplicates,
                "message": full_message,
                "hierarchy_analysis": hierarchy_analysis  # Include for additional context
            }
        else:
            # Fallback response if RAG parsing failed
            logger.warning("RAG response parsing failed, using fallback approval")
            return {
                "status": "approved",
                "suggestions": {
                    "parent_task": parent_task_id,
                    "dependencies": depends_on_tasks or [],
                    "reasoning": None
                },
                "duplicates": [],
                "message": "RAG validation unavailable, proceeding with original placement"
            }
            
    except Exception as e:
        logger.error(f"Error validating task placement: {e}", exc_info=True)
        # Return a safe default that allows task creation
        return {
            "status": "approved",
            "suggestions": {
                "parent_task": parent_task_id,
                "dependencies": depends_on_tasks or [],
                "reasoning": None
            },
            "duplicates": [],
            "message": f"Validation error: {str(e)}. Proceeding with original placement."
        }