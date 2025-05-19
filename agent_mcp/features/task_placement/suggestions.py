# Task placement suggestion parser and formatter
from typing import Dict, Any, List, Optional

def parse_rag_suggestions(rag_response: str) -> Dict[str, Any]:
    """
    Parse RAG response into structured suggestions.
    
    Args:
        rag_response: Raw text response from RAG system
        
    Returns:
        Structured dictionary of suggestions
    """
    # This is now handled directly in validator.py
    # Keeping this function for potential future use
    pass

def format_suggestions_for_agent(
    validation_result: Dict[str, Any],
    original_parent: Optional[str],
    original_dependencies: Optional[List[str]]
) -> str:
    """
    Format validation suggestions into human-readable text for agents.
    
    Args:
        validation_result: Result from validate_task_placement
        original_parent: Originally proposed parent task
        original_dependencies: Originally proposed dependencies
        
    Returns:
        Formatted message for the agent
    """
    messages = []
    
    # Add main status message
    status = validation_result.get("status", "approved")
    main_message = validation_result.get("message", "")
    
    # Check for hierarchy violations
    hierarchy_analysis = validation_result.get("hierarchy_analysis", {})
    hierarchy_violation = hierarchy_analysis.get("hierarchy_violation", False)
    
    if hierarchy_violation:
        messages.append("🚫 HIERARCHY VIOLATION: Only ONE root task is allowed!")
        messages.append(f"   Existing root task: {hierarchy_analysis.get('current_root_task_id', 'unknown')}")
        messages.append("   This task MUST have a parent.")
    
    if status == "approved":
        messages.append(f"✓ Task placement approved: {main_message}")
    elif status == "suggest_changes":
        messages.append(f"⚠️ Task placement suggestions: {main_message}")
    elif status == "warning":
        messages.append(f"⚠️ Task placement warning: {main_message}")
    elif status == "denied":
        messages.append(f"❌ Task placement denied: {main_message}")
    
    suggestions = validation_result.get("suggestions", {})
    
    # Format parent task suggestion
    suggested_parent = suggestions.get("parent_task")
    if suggested_parent != original_parent and suggested_parent is not None:
        messages.append(f"\n📁 Suggested parent task: {suggested_parent}")
        if original_parent:
            messages.append(f"   (instead of: {original_parent})")
    
    # Format dependency suggestions
    suggested_deps = suggestions.get("dependencies", [])
    original_deps = original_dependencies or []
    
    added_deps = [d for d in suggested_deps if d not in original_deps]
    removed_deps = [d for d in original_deps if d not in suggested_deps]
    
    if added_deps:
        messages.append(f"\n➕ Suggested additional dependencies: {', '.join(added_deps)}")
    
    if removed_deps:
        messages.append(f"\n➖ Suggested to remove dependencies: {', '.join(removed_deps)}")
    
    # Format reasoning if available
    reasoning = suggestions.get("reasoning")
    if reasoning:
        messages.append(f"\n💡 Reasoning: {reasoning}")
    
    # Format duplicate warnings
    duplicates = validation_result.get("duplicates", [])
    if duplicates:
        messages.append("\n⚠️ Potential duplicate tasks detected:")
        for dup in duplicates:
            similarity_pct = int(dup.get("similarity", 0) * 100)
            messages.append(
                f"   - {dup.get('title', 'Unknown')} "
                f"(ID: {dup.get('task_id', 'unknown')}, "
                f"{similarity_pct}% similar)"
            )
    
    # Add action recommendations
    if status == "suggest_changes":
        messages.append("\n🔧 Recommended actions:")
        messages.append("   1. Review the suggestions above")
        messages.append("   2. Accept suggestions with 'accept_suggestions=True'")
        messages.append("   3. Or proceed with original placement if you disagree")
    
    return "\n".join(messages)

def format_override_reason(
    agent_id: str,
    validation_result: Dict[str, Any],
    override_reason: Optional[str] = None
) -> str:
    """
    Format the reason for overriding RAG suggestions.
    
    Args:
        agent_id: ID of the agent overriding
        validation_result: Original validation result
        override_reason: Custom reason provided by agent
        
    Returns:
        Formatted override message for logging
    """
    status = validation_result.get("status", "unknown")
    suggestions = validation_result.get("suggestions", {})
    
    parts = [
        f"Agent {agent_id} overriding {status} RAG validation.",
        f"RAG suggested: parent={suggestions.get('parent_task')}, "
        f"deps={suggestions.get('dependencies', [])}",
    ]
    
    if override_reason:
        parts.append(f"Override reason: {override_reason}")
    else:
        parts.append("No override reason provided")
    
    return " | ".join(parts)

def should_escalate_to_admin(
    validation_result: Dict[str, Any],
    created_by: str
) -> bool:
    """
    Determine if validation result should be escalated to admin.
    
    Args:
        validation_result: Result from validate_task_placement
        created_by: Agent creating the task
        
    Returns:
        True if should escalate to admin
    """
    status = validation_result.get("status", "approved")
    
    # Admin never needs escalation
    if created_by == "admin":
        return False
    
    # Denied tasks should be escalated
    if status == "denied":
        return True
    
    # High similarity duplicates should be escalated
    duplicates = validation_result.get("duplicates", [])
    for dup in duplicates:
        if dup.get("similarity", 0) > 0.9:  # 90% similar
            return True
    
    # Major structural issues (if message indicates)
    message = validation_result.get("message", "").lower()
    escalation_keywords = ["critical", "major issue", "structural problem", "violates"]
    if any(keyword in message for keyword in escalation_keywords):
        return True
    
    return False