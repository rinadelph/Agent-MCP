# Agent-MCP/mcp_template/mcp_server_src/features/rag/query.py
import json
import sqlite3 # For type hinting and error handling
from typing import List, Dict, Any, Optional, Tuple

# Imports from our project
from ...core.config import (
    logger,
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSION,
    CHAT_MODEL,
    MAX_CONTEXT_TOKENS # From main.py:182
)
from ...db.connection import get_db_connection, is_vss_loadable
from ...external.openai_service import get_openai_client

# For OpenAI exceptions
import openai

# Original location: main.py lines 1432 - 1566 (ask_project_rag_tool function body)

async def query_rag_system(query_text: str) -> str:
    """
    Processes a natural language query using the RAG system.
    Fetches relevant context from live data and indexed knowledge,
    then uses an LLM to synthesize an answer.

    Args:
        query_text: The natural language question from the user.

    Returns:
        A string containing the answer or an error message.
    """
    # Get OpenAI client (main.py:1438)
    openai_client = get_openai_client()
    if not openai_client:
        logger.error("RAG Query: OpenAI client is not available. Cannot process query.")
        return "RAG Error: OpenAI client not available. Please check server configuration and OpenAI API key."

    conn = None
    answer = "An unexpected error occurred during the RAG query." # Default error message

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        live_context_results: List[Dict[str, Any]] = []
        live_task_results: List[Dict[str, Any]] = []
        vector_search_results: List[Dict[str, Any]] = [] # Store as dicts for easier access

        # --- 1. Fetch Live Context (Recently Updated) ---
        # Original main.py: lines 1445 - 1457
        try:
            cursor.execute("SELECT meta_value FROM rag_meta WHERE meta_key = ?", ('last_indexed_context',))
            last_indexed_context_row = cursor.fetchone()
            last_indexed_context_time = last_indexed_context_row['meta_value'] if last_indexed_context_row else '1970-01-01T00:00:00Z'

            cursor.execute("""
                SELECT context_key, value, description, last_updated
                FROM project_context
                WHERE last_updated > ?
                ORDER BY last_updated DESC
                LIMIT 5
            """, (last_indexed_context_time,))
            # Convert rows to dicts for easier processing
            live_context_results = [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e_live_ctx:
            logger.warning(f"RAG Query: Failed to fetch live project context: {e_live_ctx}")
        except Exception as e_live_ctx_other: # Catch any other unexpected error
            logger.warning(f"RAG Query: Unexpected error fetching live project context: {e_live_ctx_other}", exc_info=True)


        # --- 2. Fetch Live Tasks (Keyword Search) ---
        # Original main.py: lines 1459 - 1477
        try:
            query_keywords = [f'%{word.strip().lower()}%' for word in query_text.split() if len(word.strip()) > 2]
            if query_keywords:
                # Build LIKE clauses for title and description
                # Ensure each keyword is used for both title and description search
                conditions = []
                sql_params_tasks: List[str] = []
                for kw in query_keywords:
                    conditions.append("LOWER(title) LIKE ?")
                    sql_params_tasks.append(kw)
                    conditions.append("LOWER(description) LIKE ?")
                    sql_params_tasks.append(kw)
                
                if conditions:
                    # Validate that all conditions are safe (only LIKE patterns)
                    safe_conditions = []
                    for condition in conditions:
                        if condition not in ["LOWER(title) LIKE ?", "LOWER(description) LIKE ?"]:
                            logger.warning(f"RAG Query: Skipping unsafe condition: {condition}")
                            continue
                        safe_conditions.append(condition)
                    
                    if safe_conditions:
                        where_clause = ' OR '.join(safe_conditions)
                        task_query_sql = f"""
                            SELECT task_id, title, status, description, updated_at
                            FROM tasks
                            WHERE {where_clause}
                            ORDER BY updated_at DESC
                            LIMIT 5
                        """
                        cursor.execute(task_query_sql, sql_params_tasks)
                    live_task_results = [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e_live_task:
            logger.warning(f"RAG Query: Failed to fetch live tasks based on query keywords: {e_live_task}")
        except Exception as e_live_task_other:
            logger.warning(f"RAG Query: Unexpected error fetching live tasks: {e_live_task_other}", exc_info=True)


        # --- 3. Perform Vector Search (Indexed Knowledge) ---
        # Original main.py: lines 1479 - 1506
        if is_vss_loadable(): # Check global VSS status
            try:
                # Check if rag_embeddings table exists (main.py:1480-1484)
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rag_embeddings'")
                if cursor.fetchone() is not None:
                    # Embed the query (main.py:1487-1492)
                    response = openai_client.embeddings.create(
                        input=[query_text],
                        model=EMBEDDING_MODEL,
                        dimensions=EMBEDDING_DIMENSION
                    )
                    query_embedding = response.data[0].embedding
                    query_embedding_json = json.dumps(query_embedding)

                    # Search Vector Table with metadata
                    k_results = 10 # Increased to get more diverse results
                    sql_vector_search = """
                        SELECT c.chunk_text, c.source_type, c.source_ref, c.metadata, r.distance
                        FROM rag_embeddings r
                        JOIN rag_chunks c ON r.rowid = c.chunk_id
                        WHERE r.embedding MATCH ? AND k = ?
                        ORDER BY r.distance
                    """
                    cursor.execute(sql_vector_search, (query_embedding_json, k_results))
                    raw_results = cursor.fetchall()
                    
                    # Process results to parse metadata
                    for row in raw_results:
                        result = dict(row)
                        # Parse metadata JSON if present
                        if result.get('metadata'):
                            try:
                                result['metadata'] = json.loads(result['metadata'])
                            except json.JSONDecodeError:
                                result['metadata'] = None
                        vector_search_results.append(result)
                else:
                    logger.warning("RAG Query: 'rag_embeddings' table not found. Skipping vector search.")
            except sqlite3.Error as e_vec_sql:
                logger.error(f"RAG Query: Database error during vector search: {e_vec_sql}")
            except openai.APIError as e_openai_emb: # Catch OpenAI errors during embedding
                logger.error(f"RAG Query: OpenAI API error during query embedding: {e_openai_emb}")
            except Exception as e_vec_other:
                logger.error(f"RAG Query: Unexpected error during vector search part: {e_vec_other}", exc_info=True)
        else:
            logger.warning("RAG Query: Vector search (sqlite-vec) is not available. Skipping vector search.")

        # --- 4. Combine Contexts for LLM ---
        # Original main.py: lines 1509 - 1548
        context_parts: List[str] = []
        current_token_count: int = 0 # Approximate token count

        # Add Live Context
        if live_context_results:
            context_parts.append("--- Recently Updated Project Context (Live) ---")
            for item in live_context_results:
                entry_text = f"Key: {item['context_key']}\nValue: {item['value']}\nDescription: {item.get('description', 'N/A')}\n(Updated: {item['last_updated']})\n"
                entry_tokens = len(entry_text.split()) # Approximation
                if current_token_count + entry_tokens < MAX_CONTEXT_TOKENS:
                    context_parts.append(entry_text)
                    current_token_count += entry_tokens
                else: break
            context_parts.append("---------------------------------------------")

        # Add Live Tasks
        if live_task_results:
            context_parts.append("--- Potentially Relevant Tasks (Live) ---")
            for task in live_task_results:
                entry_text = f"Task ID: {task['task_id']}\nTitle: {task['title']}\nStatus: {task['status']}\nDescription: {task.get('description', 'N/A')}\n(Updated: {task['updated_at']})\n"
                entry_tokens = len(entry_text.split())
                if current_token_count + entry_tokens < MAX_CONTEXT_TOKENS:
                    context_parts.append(entry_text)
                    current_token_count += entry_tokens
                else: break
            context_parts.append("---------------------------------------")

        # Add Indexed Knowledge (Vector Search Results)
        if vector_search_results:
            context_parts.append("--- Indexed Project Knowledge (Vector Search Results) ---")
            for i, item in enumerate(vector_search_results):
                chunk_text = item['chunk_text']
                source_type = item['source_type']
                source_ref = item['source_ref']
                metadata = item.get('metadata', {})
                distance = item.get('distance', 'N/A')
                
                # Enhanced source info with metadata
                source_info = f"Source Type: {source_type}, Reference: {source_ref}"
                
                # Add code-specific metadata if available
                if metadata and source_type in ['code', 'code_summary']:
                    if metadata.get('language'):
                        source_info += f", Language: {metadata['language']}"
                    if metadata.get('section_type'):
                        source_info += f", Section: {metadata['section_type']}"
                    if metadata.get('entities'):
                        entity_names = [e.get('name', '') for e in metadata['entities']]
                        if entity_names:
                            source_info += f", Contains: {', '.join(entity_names[:3])}"
                            if len(entity_names) > 3:
                                source_info += f" (+{len(entity_names)-3} more)"
                
                entry_text = f"Retrieved Chunk {i+1} (Similarity/Distance: {distance}):\n{source_info}\nContent:\n{chunk_text}\n"
                chunk_tokens = len(entry_text.split())
                if current_token_count + chunk_tokens < MAX_CONTEXT_TOKENS:
                    context_parts.append(entry_text)
                    current_token_count += chunk_tokens
                else:
                    context_parts.append("--- [Indexed knowledge truncated due to token limit] ---")
                    break
            context_parts.append("-------------------------------------------------------")

        if not context_parts:
            logger.info(f"RAG Query: No relevant information found for query: '{query_text}'")
            answer = "No relevant information found in the project knowledge base or live data for your query."
        else:
            combined_context_str = "\n\n".join(context_parts)

            # --- 5. Call Chat Completion API ---
            # Original main.py: lines 1550 - 1562
            system_prompt_for_llm = """You are an AI assistant answering questions about a software project. 
Use the provided context, which may include recently updated live data (like project context keys or tasks) and information retrieved from an indexed knowledge base (like documentation or code summaries), to answer the user's query. 
Prioritize information from the 'Live' sections if available and relevant for time-sensitive data. 
Answer using *only* the information given in the context. If the context doesn't contain the answer, state that clearly.

Be VERBOSE and comprehensive in your responses. It's better to give too much context than too little. 
When answering, please also suggest additional context entries and queries that might be helpful for understanding this topic better.
For example, suggest related files to examine, related project context keys to check, or follow-up questions that could provide more insight.
Always err on the side of providing more detailed explanations and comprehensive information rather than brief responses."""
            
            user_message_for_llm = f"CONTEXT:\n{combined_context_str}\n\nQUERY:\n{query_text}\n\nBased *only* on the CONTEXT provided above, please answer the QUERY."

            logger.debug(f"RAG Query: Combined context for LLM (approx tokens: {current_token_count}):\n{combined_context_str[:500]}...") # Log excerpt
            logger.debug(f"RAG Query: User message for LLM:\n{user_message_for_llm[:500]}...")

            chat_response = openai_client.chat.completions.create(
                model=CHAT_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt_for_llm},
                    {"role": "user", "content": user_message_for_llm}
                ],
                temperature=0.4  # Increased for more diverse context discovery while maintaining accuracy
            )
            answer = chat_response.choices[0].message.content

    except openai.APIError as e_openai: # main.py:1563
        logger.error(f"RAG Query: OpenAI API error: {e_openai}", exc_info=True)
        answer = f"Error communicating with OpenAI: {e_openai}"
    except sqlite3.Error as e_sql: # main.py:1566
        logger.error(f"RAG Query: Database error: {e_sql}", exc_info=True)
        answer = f"Error querying RAG database: {e_sql}"
    except Exception as e_unexpected: # main.py:1569
        logger.error(f"RAG Query: Unexpected error: {e_unexpected}", exc_info=True)
        answer = f"An unexpected error occurred during the RAG query: {str(e_unexpected)}"
    finally:
        if conn:
            conn.close()

    return answer


async def query_rag_system_with_model(
    query_text: str,
    model_name: str,
    max_tokens: int = None
) -> str:
    """
    Processes a query using the RAG system with a specific OpenAI model.
    This is useful for task analysis with cheaper models while keeping 
    main RAG queries on the premium model.
    
    Args:
        query_text: The natural language question from the user.
        model_name: The OpenAI model name to use (e.g., 'gpt-3.5-turbo-16k')
        max_tokens: The maximum context tokens for this model
        
    Returns:
        A string containing the answer or an error message.
    """
    # Get OpenAI client
    openai_client = get_openai_client()
    if not openai_client:
        logger.error("RAG Query: OpenAI client is not available. Cannot process query.")
        return "RAG Error: OpenAI client not available. Please check server configuration and OpenAI API key."
    
    # Use provided max_tokens or default to the configured value
    context_limit = max_tokens if max_tokens else MAX_CONTEXT_TOKENS
    
    conn = None
    answer = "An unexpected error occurred during the RAG query."
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        live_context_results: List[Dict[str, Any]] = []
        live_task_results: List[Dict[str, Any]] = []
        vector_search_results: List[Dict[str, Any]] = []
        
        # Get live context (same as regular RAG)
        cursor.execute("SELECT context_key, value, description, last_updated FROM project_context ORDER BY last_updated DESC")
        live_context_results = [dict(row) for row in cursor.fetchall()]
        
        # Get live tasks (same as regular RAG)
        cursor.execute("""
            SELECT task_id, title, description, status, created_by, assigned_to, 
                   priority, parent_task, depends_on_tasks, created_at, updated_at 
            FROM tasks 
            WHERE status IN ('pending', 'in_progress') 
            ORDER BY updated_at DESC
        """)
        live_task_results = [dict(row) for row in cursor.fetchall()]
        
        # Get vector search results if VSS is available
        if is_vss_loadable():
            query_embedding_response = openai_client.embeddings.create(
                input=[query_text],
                model=EMBEDDING_MODEL,
                dimensions=EMBEDDING_DIMENSION
            )
            query_embedding = query_embedding_response.data[0].embedding
            
            # Perform vector search
            # Validate embedding is a list of numbers with expected dimension
            if not isinstance(query_embedding, list) or len(query_embedding) != EMBEDDING_DIMENSION:
                raise ValueError(f"Invalid query embedding: expected list of {EMBEDDING_DIMENSION} numbers")
            
            # Create safe placeholder string (just question marks)
            placeholder_str = ", ".join(["?"] * len(query_embedding))
            query_params = query_embedding + [10]  # Top 10 results
            
            # Safe to use placeholder_str since it only contains "?" characters
            vector_search_sql = f"""
                SELECT c.chunk_id, c.source_type, c.source_ref, c.chunk_text,
                       COALESCE(abs(distance), 0) as distance
                FROM rag_chunks c
                JOIN rag_embeddings e ON c.chunk_id = e.rowid
                WHERE e.embedding MATCH '[{placeholder_str}]'
                  AND k = ?
                ORDER BY distance ASC
            """
            cursor.execute(vector_search_sql, query_params)
            
            vector_search_results = [dict(row) for row in cursor.fetchall()]
        
        # Build context (same structure as regular RAG)
        context_parts = []
        current_token_count = 0
        
        # Include live context
        if live_context_results:
            context_parts.append("=== Live Project Context ===")
            for item in live_context_results:
                entry_text = f"Key: {item['context_key']}\nDescription: {item['description']}\nValue: {item['value']}\nLast Updated: {item['last_updated']}\n"
                chunk_tokens = len(entry_text.split())
                if current_token_count + chunk_tokens < context_limit:
                    context_parts.append(entry_text)
                    current_token_count += chunk_tokens
                else:
                    context_parts.append("--- [Live context truncated due to token limit] ---")
                    break
        
        # Include live tasks
        if live_task_results:
            context_parts.append("\n=== Live Task Information ===")
            for item in live_task_results:
                entry_text = f"Task ID: {item['task_id']}\nTitle: {item['title']}\nDescription: {item['description']}\nStatus: {item['status']}\n"
                entry_text += f"Priority: {item['priority']}\nAssigned To: {item['assigned_to']}\nCreated By: {item['created_by']}\n"
                entry_text += f"Parent Task: {item['parent_task']}\nDependencies: {item['depends_on_tasks']}\n"
                entry_text += f"Created: {item['created_at']}\nUpdated: {item['updated_at']}\n"
                chunk_tokens = len(entry_text.split())
                if current_token_count + chunk_tokens < context_limit:
                    context_parts.append(entry_text)
                    current_token_count += chunk_tokens
                else:
                    context_parts.append("--- [Live tasks truncated due to token limit] ---")
                    break
        
        # Include vector search results
        if vector_search_results:
            context_parts.append("\n=== Retrieved from Indexed Knowledge ===")
            for i, item in enumerate(vector_search_results):
                chunk_text = item['chunk_text']
                source_info = f"Source Type: {item['source_type']}, Reference: {item['source_ref']}"
                distance = item.get('distance', 'N/A')
                entry_text = f"Retrieved Chunk {i+1} (Similarity/Distance: {distance}):\n{source_info}\nContent:\n{chunk_text}\n"
                chunk_tokens = len(entry_text.split())
                if current_token_count + chunk_tokens < context_limit:
                    context_parts.append(entry_text)
                    current_token_count += chunk_tokens
                else:
                    context_parts.append("--- [Indexed knowledge truncated due to token limit] ---")
                    break
        
        if not context_parts:
            logger.info(f"RAG Query: No relevant information found for query: '{query_text}'")
            answer = "No relevant information found in the project knowledge base or live data for your query."
        else:
            combined_context_str = "\n\n".join(context_parts)
            
            # Call Chat Completion API with specified model
            system_prompt_for_llm = """You are an AI assistant specializing in task hierarchy analysis and project structure optimization. 
You must CRITICALLY THINK about task placement, dependencies, and hierarchical relationships.
Use the provided context to make intelligent recommendations about task organization.
Be strict about the single root task rule and logical task relationships.

Be VERBOSE and comprehensive in your analysis. It's better to give too much context than too little.
When making recommendations, suggest additional context entries and queries that might be helpful for understanding task relationships better.
Consider suggesting related files to examine, project context keys to check, or follow-up questions for deeper task analysis.
Provide detailed explanations for your reasoning and comprehensive information rather than brief responses.
Answer in the exact JSON format requested, but include thorough explanations in your reasoning sections."""
            
            user_message_for_llm = f"CONTEXT:\n{combined_context_str}\n\nQUERY:\n{query_text}\n\nBased on the CONTEXT provided above, please answer the QUERY."
            
            logger.info(f"Task Analysis Query: Using model {model_name} with {context_limit} token limit")
            
            # Use the specified model for this query
            chat_response = openai_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt_for_llm},
                    {"role": "user", "content": user_message_for_llm}
                ],
                temperature=0.4  # Increased for more diverse analysis while maintaining JSON consistency
            )
            answer = chat_response.choices[0].message.content
            
    except Exception as e:
        logger.error(f"RAG Query with model {model_name}: Error: {e}", exc_info=True)
        answer = f"Error during RAG query with {model_name}: {str(e)}"
    finally:
        if conn:
            conn.close()
    
    return answer