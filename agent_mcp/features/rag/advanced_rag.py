# Agent-MCP Advanced RAG System
"""
Advanced RAG system with multi-modal embeddings, semantic search improvements,
context-aware query optimization, and performance monitoring.
"""

import asyncio
import json
import time
import sqlite3
import hashlib
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import numpy as np
from datetime import datetime, timedelta

# OpenAI imports
try:
    import openai
    from openai import AsyncOpenAI
except ImportError:
    openai = None
    AsyncOpenAI = None

# Local imports
from ...core.config import logger, get_project_dir
from ...db.connection import get_db_connection
from ...external.openai_service import get_openai_client
from .chunking import simple_chunker, markdown_aware_chunker
from .code_chunking import chunk_code_aware, detect_language_family


class EmbeddingType(Enum):
    """Types of embeddings supported by the advanced RAG system."""
    TEXT = "text"
    CODE = "code"
    IMAGE = "image"
    AUDIO = "audio"
    MULTIMODAL = "multimodal"


class QueryType(Enum):
    """Types of queries for context-aware optimization."""
    FACTUAL = "factual"
    ANALYTICAL = "analytical"
    CREATIVE = "creative"
    DEBUGGING = "debugging"
    DOCUMENTATION = "documentation"
    CODE_REVIEW = "code_review"


@dataclass
class PerformanceMetrics:
    """Performance metrics for RAG operations."""
    query_time: float = 0.0
    embedding_time: float = 0.0
    search_time: float = 0.0
    synthesis_time: float = 0.0
    total_tokens_used: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    embedding_requests: int = 0
    search_requests: int = 0
    synthesis_requests: int = 0
    error_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class QueryContext:
    """Context information for query optimization."""
    query_type: QueryType
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    previous_queries: List[str] = field(default_factory=list)
    domain_context: Dict[str, Any] = field(default_factory=dict)
    preferred_sources: List[str] = field(default_factory=list)
    complexity_level: str = "medium"  # low, medium, high
    time_sensitivity: str = "normal"  # low, normal, high, urgent


@dataclass
class MultiModalEmbedding:
    """Multi-modal embedding representation."""
    text_embedding: Optional[List[float]] = None
    code_embedding: Optional[List[float]] = None
    image_embedding: Optional[List[float]] = None
    audio_embedding: Optional[List[float]] = None
    combined_embedding: Optional[List[float]] = None
    embedding_type: EmbeddingType = EmbeddingType.TEXT
    metadata: Dict[str, Any] = field(default_factory=dict)


class AdvancedRAGSystem:
    """Advanced RAG system with multi-modal support and performance monitoring."""
    
    def __init__(self):
        self.performance_metrics: List[PerformanceMetrics] = []
        self.query_cache: Dict[str, Any] = {}
        self.embedding_cache: Dict[str, MultiModalEmbedding] = {}
        self.context_history: Dict[str, List[QueryContext]] = {}
        self.model_configs = {
            "text": "text-embedding-3-large",
            "code": "text-embedding-3-large",
            "image": "text-embedding-3-large",  # Placeholder for image embeddings
            "multimodal": "text-embedding-3-large"
        }
        
    async def get_embeddings_multi_modal(
        self, 
        content: str, 
        content_type: EmbeddingType,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MultiModalEmbedding:
        """
        Generate multi-modal embeddings for different content types.
        
        Args:
            content: The content to embed
            content_type: Type of content (text, code, image, etc.)
            metadata: Additional metadata for the embedding
            
        Returns:
            MultiModalEmbedding object with appropriate embeddings
        """
        start_time = time.time()
        
        # Check cache first
        cache_key = self._generate_cache_key(content, content_type)
        if cache_key in self.embedding_cache:
            logger.debug(f"Cache hit for embedding: {cache_key[:50]}...")
            return self.embedding_cache[cache_key]
        
        try:
            openai_client = get_openai_client()
            if not openai_client:
                raise Exception("OpenAI client not available")
            
            embedding = MultiModalEmbedding(
                embedding_type=content_type,
                metadata=metadata or {}
            )
            
            # Generate embeddings based on content type
            if content_type == EmbeddingType.TEXT:
                response = await openai_client.embeddings.create(
                    model=self.model_configs["text"],
                    input=content,
                    encoding_format="float"
                )
                embedding.text_embedding = response.data[0].embedding
                embedding.combined_embedding = embedding.text_embedding
                
            elif content_type == EmbeddingType.CODE:
                # Use specialized code embedding model or preprocessing
                processed_content = self._preprocess_code_content(content)
                response = await openai_client.embeddings.create(
                    model=self.model_configs["code"],
                    input=processed_content,
                    encoding_format="float"
                )
                embedding.code_embedding = response.data[0].embedding
                embedding.combined_embedding = embedding.code_embedding
                
            elif content_type == EmbeddingType.MULTIMODAL:
                # For multimodal content, generate multiple embeddings and combine
                text_parts = self._extract_text_parts(content)
                code_parts = self._extract_code_parts(content)
                
                embeddings = []
                if text_parts:
                    text_response = await openai_client.embeddings.create(
                        model=self.model_configs["text"],
                        input=text_parts,
                        encoding_format="float"
                    )
                    embeddings.extend([data.embedding for data in text_response.data])
                
                if code_parts:
                    processed_code = [self._preprocess_code_content(part) for part in code_parts]
                    code_response = await openai_client.embeddings.create(
                        model=self.model_configs["code"],
                        input=processed_code,
                        encoding_format="float"
                    )
                    embeddings.extend([data.embedding for data in code_response.data])
                
                # Combine embeddings using weighted average
                if embeddings:
                    embedding.combined_embedding = self._combine_embeddings(embeddings)
                    embedding.text_embedding = embeddings[0] if len(embeddings) > 0 else None
                    embedding.code_embedding = embeddings[-1] if len(embeddings) > 1 else None
            
            # Cache the embedding
            self.embedding_cache[cache_key] = embedding
            
            # Record performance metrics
            embedding_time = time.time() - start_time
            self._record_metric("embedding_time", embedding_time)
            self._record_metric("embedding_requests", 1)
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating multi-modal embeddings: {e}")
            self._record_metric("error_count", 1)
            raise
    
    def _preprocess_code_content(self, code: str) -> str:
        """Preprocess code content for better embedding quality."""
        # Remove comments, normalize whitespace, extract key identifiers
        lines = code.split('\n')
        processed_lines = []
        
        for line in lines:
            # Remove comments
            if '#' in line:
                line = line.split('#')[0]
            if '//' in line:
                line = line.split('//')[0]
            if '/*' in line and '*/' in line:
                line = line.replace('/*', '').replace('*/', '')
            
            # Keep only meaningful lines
            if line.strip() and not line.strip().startswith('#'):
                processed_lines.append(line.strip())
        
        return '\n'.join(processed_lines)
    
    def _extract_text_parts(self, content: str) -> List[str]:
        """Extract text parts from multimodal content."""
        # Simple extraction - could be enhanced with NLP
        parts = []
        lines = content.split('\n')
        
        for line in lines:
            if not line.strip().startswith(('#', '//', '/*', '*/', 'import', 'from', 'def ', 'class ')):
                if len(line.strip()) > 10:  # Meaningful text
                    parts.append(line.strip())
        
        return parts[:10]  # Limit to 10 parts
    
    def _extract_code_parts(self, content: str) -> List[str]:
        """Extract code parts from multimodal content."""
        parts = []
        lines = content.split('\n')
        
        for line in lines:
            if line.strip().startswith(('import ', 'from ', 'def ', 'class ', 'if ', 'for ', 'while ')):
                parts.append(line.strip())
        
        return parts[:10]  # Limit to 10 parts
    
    def _combine_embeddings(self, embeddings: List[List[float]]) -> List[float]:
        """Combine multiple embeddings using weighted average."""
        if not embeddings:
            return []
        
        # Simple average - could be enhanced with attention mechanisms
        combined = np.mean(embeddings, axis=0)
        return combined.tolist()
    
    def _generate_cache_key(self, content: str, content_type: EmbeddingType) -> str:
        """Generate cache key for embeddings."""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        return f"{content_type.value}_{content_hash}"
    
    async def semantic_search_advanced(
        self,
        query: str,
        query_context: QueryContext,
        max_results: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Advanced semantic search with context-aware optimization.
        
        Args:
            query: The search query
            query_context: Context information for optimization
            max_results: Maximum number of results to return
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of search results with metadata
        """
        start_time = time.time()
        
        try:
            # Optimize query based on context
            optimized_query = self._optimize_query_for_context(query, query_context)
            
            # Generate query embedding
            query_embedding = await self.get_embeddings_multi_modal(
                optimized_query, 
                EmbeddingType.TEXT
            )
            
            # Perform vector search with context-aware filtering
            results = await self._vector_search_advanced(
                query_embedding.combined_embedding,
                query_context,
                max_results,
                similarity_threshold
            )
            
            # Apply post-processing based on query type
            processed_results = self._post_process_results(results, query_context)
            
            # Record performance metrics
            search_time = time.time() - start_time
            self._record_metric("search_time", search_time)
            self._record_metric("search_requests", 1)
            
            return processed_results
            
        except Exception as e:
            logger.error(f"Error in advanced semantic search: {e}")
            self._record_metric("error_count", 1)
            return []
    
    def _optimize_query_for_context(self, query: str, context: QueryContext) -> str:
        """Optimize query based on context information."""
        optimized = query
        
        # Add domain-specific terms based on context
        if context.domain_context:
            domain_terms = " ".join(context.domain_context.keys())
            optimized = f"{optimized} {domain_terms}"
        
        # Add complexity indicators
        if context.complexity_level == "high":
            optimized = f"{optimized} detailed comprehensive"
        elif context.complexity_level == "low":
            optimized = f"{optimized} simple basic"
        
        # Add time sensitivity indicators
        if context.time_sensitivity == "urgent":
            optimized = f"{optimized} urgent immediate"
        
        # Add query type specific terms
        if context.query_type == QueryType.DEBUGGING:
            optimized = f"{optimized} error fix debug issue"
        elif context.query_type == QueryType.CODE_REVIEW:
            optimized = f"{optimized} review code quality best practices"
        elif context.query_type == QueryType.DOCUMENTATION:
            optimized = f"{optimized} documentation guide tutorial"
        
        return optimized
    
    async def _vector_search_advanced(
        self,
        query_embedding: List[float],
        context: QueryContext,
        max_results: int,
        similarity_threshold: float
    ) -> List[Dict[str, Any]]:
        """Advanced vector search with context-aware filtering."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Convert embedding to SQLite format
            embedding_blob = sqlite3.Binary(json.dumps(query_embedding).encode())
            
            # Build context-aware query
            base_query = """
                SELECT 
                    content_key,
                    content,
                    embedding,
                    content_type,
                    metadata,
                    similarity(embedding, ?) as score
                FROM rag_embeddings
                WHERE similarity(embedding, ?) > ?
            """
            
            params = [embedding_blob, embedding_blob, similarity_threshold]
            
            # Add context filters
            if context.preferred_sources:
                source_filter = " AND content_key IN ({})".format(
                    ",".join(["?"] * len(context.preferred_sources))
                )
                base_query += source_filter
                params.extend(context.preferred_sources)
            
            # Add content type filters based on query type
            if context.query_type == QueryType.CODE_REVIEW:
                base_query += " AND (content_type = 'code' OR content_type = 'multimodal')"
            elif context.query_type == QueryType.DOCUMENTATION:
                base_query += " AND (content_type = 'text' OR content_type = 'multimodal')"
            
            base_query += " ORDER BY score DESC LIMIT ?"
            params.append(max_results)
            
            cursor.execute(base_query, params)
            results = []
            
            for row in cursor.fetchall():
                results.append({
                    "content_key": row["content_key"],
                    "content": row["content"],
                    "content_type": row["content_type"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "score": row["score"]
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            return []
        finally:
            conn.close()
    
    def _post_process_results(
        self, 
        results: List[Dict[str, Any]], 
        context: QueryContext
    ) -> List[Dict[str, Any]]:
        """Post-process search results based on query context."""
        processed = []
        
        for result in results:
            # Add context-specific metadata
            result["query_context"] = {
                "query_type": context.query_type.value,
                "complexity_level": context.complexity_level,
                "time_sensitivity": context.time_sensitivity
            }
            
            # Apply content-specific processing
            if context.query_type == QueryType.CODE_REVIEW:
                result["content"] = self._highlight_code_issues(result["content"])
            elif context.query_type == QueryType.DEBUGGING:
                result["content"] = self._highlight_debug_info(result["content"])
            
            processed.append(result)
        
        return processed
    
    def _highlight_code_issues(self, content: str) -> str:
        """Highlight potential code issues for review."""
        # Simple highlighting - could be enhanced with AST analysis
        highlighted = content
        issues = ["TODO", "FIXME", "HACK", "XXX", "BUG"]
        
        for issue in issues:
            highlighted = highlighted.replace(issue, f"**{issue}**")
        
        return highlighted
    
    def _highlight_debug_info(self, content: str) -> str:
        """Highlight debug-related information."""
        # Simple highlighting - could be enhanced with error pattern detection
        highlighted = content
        debug_terms = ["error", "exception", "fail", "crash", "bug", "debug"]
        
        for term in debug_terms:
            highlighted = highlighted.replace(term, f"**{term}**")
        
        return highlighted
    
    async def query_with_context_optimization(
        self,
        query: str,
        query_context: QueryContext,
        max_tokens: int = 1000
    ) -> Tuple[str, PerformanceMetrics]:
        """
        Query the RAG system with context-aware optimization.
        
        Args:
            query: The natural language query
            query_context: Context information for optimization
            max_tokens: Maximum tokens for response
            
        Returns:
            Tuple of (response, performance_metrics)
        """
        start_time = time.time()
        metrics = PerformanceMetrics()
        
        try:
            # Perform advanced semantic search
            search_results = await self.semantic_search_advanced(
                query, query_context
            )
            
            if not search_results:
                return "No relevant information found.", metrics
            
            # Synthesize response based on query type
            response = await self._synthesize_response_advanced(
                query, search_results, query_context, max_tokens
            )
            
            # Record final metrics
            total_time = time.time() - start_time
            metrics.query_time = total_time
            metrics.timestamp = datetime.now()
            
            return response, metrics
            
        except Exception as e:
            logger.error(f"Error in context-optimized query: {e}")
            metrics.error_count = 1
            return f"Error processing query: {str(e)}", metrics
    
    async def _synthesize_response_advanced(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        context: QueryContext,
        max_tokens: int
    ) -> str:
        """Synthesize response using advanced techniques based on query type."""
        start_time = time.time()
        
        try:
            openai_client = get_openai_client()
            if not openai_client:
                return "Error: OpenAI client not available"
            
            # Prepare context for synthesis
            context_str = self._prepare_context_for_synthesis(search_results, context)
            
            # Create system prompt based on query type
            system_prompt = self._create_system_prompt_for_query_type(context.query_type)
            
            # Generate response
            response = await openai_client.chat.completions.create(
                model="gpt-4.1-2025-04-14",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Query: {query}\n\nContext:\n{context_str}"}
                ],
                max_tokens=max_tokens,
                temperature=0.3
            )
            
            synthesis_time = time.time() - start_time
            self._record_metric("synthesis_time", synthesis_time)
            self._record_metric("synthesis_requests", 1)
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error in response synthesis: {e}")
            return f"Error synthesizing response: {str(e)}"
    
    def _prepare_context_for_synthesis(
        self, 
        search_results: List[Dict[str, Any]], 
        context: QueryContext
    ) -> str:
        """Prepare context string for response synthesis."""
        context_parts = []
        
        for i, result in enumerate(search_results[:5]):  # Limit to top 5
            content = result["content"]
            score = result["score"]
            content_type = result["content_type"]
            
            context_parts.append(f"Source {i+1} (Score: {score:.3f}, Type: {content_type}):\n{content}\n")
        
        return "\n".join(context_parts)
    
    def _create_system_prompt_for_query_type(self, query_type: QueryType) -> str:
        """Create system prompt based on query type."""
        base_prompt = "You are an advanced AI assistant with access to a comprehensive knowledge base. "
        
        if query_type == QueryType.DEBUGGING:
            return base_prompt + """
            Focus on identifying and explaining potential issues, errors, or bugs in the provided context.
            Provide clear, actionable debugging advice and suggest fixes where possible.
            """
        elif query_type == QueryType.CODE_REVIEW:
            return base_prompt + """
            Conduct a thorough code review focusing on best practices, potential issues, 
            performance considerations, and maintainability. Provide constructive feedback.
            """
        elif query_type == QueryType.DOCUMENTATION:
            return base_prompt + """
            Provide clear, comprehensive documentation and explanations. Focus on clarity,
            completeness, and usefulness for the intended audience.
            """
        elif query_type == QueryType.ANALYTICAL:
            return base_prompt + """
            Provide detailed analysis and insights. Consider multiple perspectives and
            provide evidence-based conclusions.
            """
        else:
            return base_prompt + "Provide accurate, helpful, and comprehensive responses."
    
    def _record_metric(self, metric_name: str, value: Union[float, int]) -> None:
        """Record a performance metric."""
        if not self.performance_metrics:
            self.performance_metrics.append(PerformanceMetrics())
        
        current_metrics = self.performance_metrics[-1]
        if hasattr(current_metrics, metric_name):
            current_value = getattr(current_metrics, metric_name)
            if isinstance(current_value, (int, float)):
                setattr(current_metrics, metric_name, current_value + value)
    
    def get_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate performance report for the specified time period."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [
            m for m in self.performance_metrics 
            if m.timestamp > cutoff_time
        ]
        
        if not recent_metrics:
            return {"error": "No metrics available for the specified time period"}
        
        report = {
            "time_period_hours": hours,
            "total_queries": len(recent_metrics),
            "average_query_time": np.mean([m.query_time for m in recent_metrics]),
            "average_embedding_time": np.mean([m.embedding_time for m in recent_metrics]),
            "average_search_time": np.mean([m.search_time for m in recent_metrics]),
            "average_synthesis_time": np.mean([m.synthesis_time for m in recent_metrics]),
            "total_tokens_used": sum([m.total_tokens_used for m in recent_metrics]),
            "cache_hit_rate": sum([m.cache_hits for m in recent_metrics]) / 
                            max(sum([m.cache_hits + m.cache_misses for m in recent_metrics]), 1),
            "error_rate": sum([m.error_count for m in recent_metrics]) / len(recent_metrics),
            "embedding_requests": sum([m.embedding_requests for m in recent_metrics]),
            "search_requests": sum([m.search_requests for m in recent_metrics]),
            "synthesis_requests": sum([m.synthesis_requests for m in recent_metrics])
        }
        
        return report
    
    def clear_cache(self) -> None:
        """Clear all caches."""
        self.query_cache.clear()
        self.embedding_cache.clear()
        logger.info("Advanced RAG system caches cleared")


# Global instance
advanced_rag_system = AdvancedRAGSystem()
