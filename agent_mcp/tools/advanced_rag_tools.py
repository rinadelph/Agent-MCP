# Agent-MCP Advanced RAG Tools
"""
Tools for integrating the advanced RAG system with multi-modal embeddings,
semantic search improvements, context-aware query optimization, and performance monitoring.
"""

import json
from typing import List, Dict, Any, Optional
import mcp.types as mcp_types

from .registry import register_tool
from ..core.config import logger
from ..core import globals as g
from ..core.auth import verify_token, get_agent_id
from ..utils.audit_utils import log_audit
from ..features.rag.advanced_rag import (
    advanced_rag_system,
    QueryContext,
    QueryType,
    EmbeddingType,
    PerformanceMetrics
)


async def advanced_rag_query_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    """
    Query the advanced RAG system with context-aware optimization.
    
    Args:
        token: Authentication token
        query: The natural language query
        query_type: Type of query (factual, analytical, creative, debugging, documentation, code_review)
        complexity_level: Complexity level (low, medium, high)
        time_sensitivity: Time sensitivity (low, normal, high, urgent)
        max_tokens: Maximum tokens for response
        user_id: Optional user ID for context
        session_id: Optional session ID for context
        domain_context: Optional domain context dictionary
        preferred_sources: Optional list of preferred source keys
    """
    token = arguments.get("token")
    query = arguments.get("query")
    query_type_str = arguments.get("query_type", "factual")
    complexity_level = arguments.get("complexity_level", "medium")
    time_sensitivity = arguments.get("time_sensitivity", "normal")
    max_tokens = arguments.get("max_tokens", 1000)
    user_id = arguments.get("user_id")
    session_id = arguments.get("session_id")
    domain_context = arguments.get("domain_context", {})
    preferred_sources = arguments.get("preferred_sources", [])
    
    # Authentication
    agent_id = get_agent_id(token)
    if not agent_id:
        return [mcp_types.TextContent(type="text", text="Unauthorized: Valid token required")]
    
    # Validation
    if not query:
        return [mcp_types.TextContent(type="text", text="Error: Query is required")]
    
    try:
        # Convert query type string to enum
        query_type = QueryType[query_type_str.upper()]
    except KeyError:
        return [mcp_types.TextContent(type="text", text=f"Error: Invalid query type '{query_type_str}'")]
    
    # Create query context
    query_context = QueryContext(
        query_type=query_type,
        user_id=user_id,
        session_id=session_id,
        domain_context=domain_context,
        preferred_sources=preferred_sources,
        complexity_level=complexity_level,
        time_sensitivity=time_sensitivity
    )
    
    try:
        # Execute advanced RAG query
        response, metrics = await advanced_rag_system.query_with_context_optimization(
            query=query,
            query_context=query_context,
            max_tokens=max_tokens
        )
        
        # Log audit
        log_audit(agent_id, "advanced_rag_query", {
            "query": query,
            "query_type": query_type_str,
            "complexity_level": complexity_level,
            "time_sensitivity": time_sensitivity,
            "response_length": len(response),
            "performance_metrics": {
                "query_time": metrics.query_time,
                "embedding_time": metrics.embedding_time,
                "search_time": metrics.search_time,
                "synthesis_time": metrics.synthesis_time
            }
        })
        
        return [mcp_types.TextContent(type="text", text=response)]
        
    except Exception as e:
        logger.error(f"Error in advanced RAG query: {e}")
        return [mcp_types.TextContent(type="text", text=f"Error processing query: {str(e)}")]


async def multi_modal_embedding_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    """
    Generate multi-modal embeddings for different content types.
    
    Args:
        token: Authentication token
        content: The content to embed
        content_type: Type of content (text, code, image, audio, multimodal)
        metadata: Optional metadata for the embedding
    """
    token = arguments.get("token")
    content = arguments.get("content")
    content_type_str = arguments.get("content_type", "text")
    metadata = arguments.get("metadata", {})
    
    # Authentication
    agent_id = get_agent_id(token)
    if not agent_id:
        return [mcp_types.TextContent(type="text", text="Unauthorized: Valid token required")]
    
    # Validation
    if not content:
        return [mcp_types.TextContent(type="text", text="Error: Content is required")]
    
    try:
        # Convert content type string to enum
        content_type = EmbeddingType[content_type_str.upper()]
    except KeyError:
        return [mcp_types.TextContent(type="text", text=f"Error: Invalid content type '{content_type_str}'")]
    
    try:
        # Generate multi-modal embedding
        embedding = await advanced_rag_system.get_embeddings_multi_modal(
            content=content,
            content_type=content_type,
            metadata=metadata
        )
        
        # Log audit
        log_audit(agent_id, "multi_modal_embedding", {
            "content_type": content_type_str,
            "content_length": len(content),
            "embedding_type": embedding.embedding_type.value,
            "has_text_embedding": embedding.text_embedding is not None,
            "has_code_embedding": embedding.code_embedding is not None,
            "has_combined_embedding": embedding.combined_embedding is not None
        })
        
        # Return embedding information
        result = {
            "embedding_type": embedding.embedding_type.value,
            "text_embedding_length": len(embedding.text_embedding) if embedding.text_embedding else 0,
            "code_embedding_length": len(embedding.code_embedding) if embedding.code_embedding else 0,
            "combined_embedding_length": len(embedding.combined_embedding) if embedding.combined_embedding else 0,
            "metadata": embedding.metadata
        }
        
        return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]
        
    except Exception as e:
        logger.error(f"Error generating multi-modal embedding: {e}")
        return [mcp_types.TextContent(type="text", text=f"Error generating embedding: {str(e)}")]


async def advanced_semantic_search_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    """
    Perform advanced semantic search with context-aware optimization.
    
    Args:
        token: Authentication token
        query: The search query
        query_type: Type of query (factual, analytical, creative, debugging, documentation, code_review)
        max_results: Maximum number of results to return
        similarity_threshold: Minimum similarity score
        complexity_level: Complexity level (low, medium, high)
        time_sensitivity: Time sensitivity (low, normal, high, urgent)
        domain_context: Optional domain context dictionary
        preferred_sources: Optional list of preferred source keys
    """
    token = arguments.get("token")
    query = arguments.get("query")
    query_type_str = arguments.get("query_type", "factual")
    max_results = arguments.get("max_results", 10)
    similarity_threshold = arguments.get("similarity_threshold", 0.7)
    complexity_level = arguments.get("complexity_level", "medium")
    time_sensitivity = arguments.get("time_sensitivity", "normal")
    domain_context = arguments.get("domain_context", {})
    preferred_sources = arguments.get("preferred_sources", [])
    
    # Authentication
    agent_id = get_agent_id(token)
    if not agent_id:
        return [mcp_types.TextContent(type="text", text="Unauthorized: Valid token required")]
    
    # Validation
    if not query:
        return [mcp_types.TextContent(type="text", text="Error: Query is required")]
    
    try:
        # Convert query type string to enum
        query_type = QueryType[query_type_str.upper()]
    except KeyError:
        return [mcp_types.TextContent(type="text", text=f"Error: Invalid query type '{query_type_str}'")]
    
    # Create query context
    query_context = QueryContext(
        query_type=query_type,
        domain_context=domain_context,
        preferred_sources=preferred_sources,
        complexity_level=complexity_level,
        time_sensitivity=time_sensitivity
    )
    
    try:
        # Perform advanced semantic search
        results = await advanced_rag_system.semantic_search_advanced(
            query=query,
            query_context=query_context,
            max_results=max_results,
            similarity_threshold=similarity_threshold
        )
        
        # Log audit
        log_audit(agent_id, "advanced_semantic_search", {
            "query": query,
            "query_type": query_type_str,
            "max_results": max_results,
            "similarity_threshold": similarity_threshold,
            "results_count": len(results)
        })
        
        # Return search results
        return [mcp_types.TextContent(type="text", text=json.dumps(results, indent=2))]
        
    except Exception as e:
        logger.error(f"Error in advanced semantic search: {e}")
        return [mcp_types.TextContent(type="text", text=f"Error performing search: {str(e)}")]


async def rag_performance_report_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    """
    Get performance report for the advanced RAG system.
    
    Args:
        token: Authentication token
        hours: Number of hours to include in the report (default: 24)
    """
    token = arguments.get("token")
    hours = arguments.get("hours", 24)
    
    # Authentication
    agent_id = get_agent_id(token)
    if not agent_id:
        return [mcp_types.TextContent(type="text", text="Unauthorized: Valid token required")]
    
    # Admin check for performance reports
    is_admin = verify_token(token, "admin")
    if not is_admin:
        return [mcp_types.TextContent(type="text", text="Error: Admin privileges required for performance reports")]
    
    try:
        # Get performance report
        report = advanced_rag_system.get_performance_report(hours=hours)
        
        # Log audit
        log_audit(agent_id, "rag_performance_report", {
            "hours": hours,
            "report_keys": list(report.keys())
        })
        
        # Return performance report
        return [mcp_types.TextContent(type="text", text=json.dumps(report, indent=2))]
        
    except Exception as e:
        logger.error(f"Error getting RAG performance report: {e}")
        return [mcp_types.TextContent(type="text", text=f"Error getting performance report: {str(e)}")]


async def clear_rag_cache_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    """
    Clear all caches in the advanced RAG system.
    
    Args:
        token: Authentication token
    """
    token = arguments.get("token")
    
    # Authentication
    agent_id = get_agent_id(token)
    if not agent_id:
        return [mcp_types.TextContent(type="text", text="Unauthorized: Valid token required")]
    
    # Admin check for cache clearing
    is_admin = verify_token(token, "admin")
    if not is_admin:
        return [mcp_types.TextContent(type="text", text="Error: Admin privileges required for cache operations")]
    
    try:
        # Clear RAG system caches
        advanced_rag_system.clear_cache()
        
        # Log audit
        log_audit(agent_id, "clear_rag_cache", {})
        
        return [mcp_types.TextContent(type="text", text="Advanced RAG system caches cleared successfully")]
        
    except Exception as e:
        logger.error(f"Error clearing RAG cache: {e}")
        return [mcp_types.TextContent(type="text", text=f"Error clearing cache: {str(e)}")]


def register_advanced_rag_tools():
    """Register all advanced RAG tools."""
    
    # Advanced RAG Query Tool
    register_tool(
        name="advanced_rag_query",
        description="Query the advanced RAG system with context-aware optimization, multi-modal embeddings, and performance monitoring.",
        input_schema={
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Authentication token"},
                "query": {"type": "string", "description": "The natural language query"},
                "query_type": {
                    "type": "string", 
                    "enum": ["factual", "analytical", "creative", "debugging", "documentation", "code_review"],
                    "description": "Type of query for context-aware optimization"
                },
                "complexity_level": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Complexity level for query optimization"
                },
                "time_sensitivity": {
                    "type": "string",
                    "enum": ["low", "normal", "high", "urgent"],
                    "description": "Time sensitivity for query optimization"
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Maximum tokens for response",
                    "default": 1000
                },
                "user_id": {
                    "type": "string",
                    "description": "Optional user ID for context"
                },
                "session_id": {
                    "type": "string",
                    "description": "Optional session ID for context"
                },
                "domain_context": {
                    "type": "object",
                    "description": "Optional domain context dictionary"
                },
                "preferred_sources": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of preferred source keys"
                }
            },
            "required": ["token", "query"],
            "additionalProperties": False
        },
        implementation=advanced_rag_query_tool_impl
    )
    
    # Multi-Modal Embedding Tool
    register_tool(
        name="multi_modal_embedding",
        description="Generate multi-modal embeddings for different content types (text, code, image, audio, multimodal).",
        input_schema={
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Authentication token"},
                "content": {"type": "string", "description": "The content to embed"},
                "content_type": {
                    "type": "string",
                    "enum": ["text", "code", "image", "audio", "multimodal"],
                    "description": "Type of content for embedding"
                },
                "metadata": {
                    "type": "object",
                    "description": "Optional metadata for the embedding"
                }
            },
            "required": ["token", "content"],
            "additionalProperties": False
        },
        implementation=multi_modal_embedding_tool_impl
    )
    
    # Advanced Semantic Search Tool
    register_tool(
        name="advanced_semantic_search",
        description="Perform advanced semantic search with context-aware optimization and multi-modal support.",
        input_schema={
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Authentication token"},
                "query": {"type": "string", "description": "The search query"},
                "query_type": {
                    "type": "string", 
                    "enum": ["factual", "analytical", "creative", "debugging", "documentation", "code_review"],
                    "description": "Type of query for context-aware optimization"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": 10
                },
                "similarity_threshold": {
                    "type": "number",
                    "description": "Minimum similarity score",
                    "default": 0.7
                },
                "complexity_level": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Complexity level for search optimization"
                },
                "time_sensitivity": {
                    "type": "string",
                    "enum": ["low", "normal", "high", "urgent"],
                    "description": "Time sensitivity for search optimization"
                },
                "domain_context": {
                    "type": "object",
                    "description": "Optional domain context dictionary"
                },
                "preferred_sources": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of preferred source keys"
                }
            },
            "required": ["token", "query"],
            "additionalProperties": False
        },
        implementation=advanced_semantic_search_tool_impl
    )
    
    # RAG Performance Report Tool
    register_tool(
        name="rag_performance_report",
        description="Get performance report for the advanced RAG system with detailed metrics and monitoring data.",
        input_schema={
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Authentication token"},
                "hours": {
                    "type": "integer",
                    "description": "Number of hours to include in the report",
                    "default": 24
                }
            },
            "required": ["token"],
            "additionalProperties": False
        },
        implementation=rag_performance_report_tool_impl
    )
    
    # Clear RAG Cache Tool
    register_tool(
        name="clear_rag_cache",
        description="Clear all caches in the advanced RAG system (admin only).",
        input_schema={
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Authentication token"}
            },
            "required": ["token"],
            "additionalProperties": False
        },
        implementation=clear_rag_cache_tool_impl
    )


# Register tools when module is imported
register_advanced_rag_tools()
