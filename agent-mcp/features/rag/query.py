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

# For type hinting the OpenAI client
# import openai # Not strictly needed if we don't type hint client explicitly beyond 'Any'

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
                    task_query_sql = f"""
                        SELECT task_id, title, status, description, updated_at
                        FROM tasks
                        WHERE {' OR '.join(conditions)}
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

                    # Search Vector Table (main.py:1495-1502)
                    k_results = 5 # Number of results to retrieve
                    # The original query used `k = ?2`. sqlite-vec's `MATCH` clause takes `k` as a parameter.
                    # The exact syntax for parameterizing `k` in `MATCH ... AND k = ?` might vary
                    # or might not be directly supported. It's often part of the `LIMIT` clause or intrinsic to `MATCH`.
                    # Assuming `sqlite-vec` supports `LIMIT` correctly with `MATCH`.
                    # Let's adjust to a more standard way or how `sqlite-vec` expects it.
                    # If `k` is part of `MATCH`, it's usually `knn_search(embedding, k)`.
                    # The original query `WHERE r.embedding MATCH ?1 AND k = ?2 ORDER BY r.distance`
                    # implies `k` is a parameter to the MATCH.
                    # For `vec0`, the `k` parameter is typically part of the `MATCH` clause itself or handled by `LIMIT`.
                    # The original query seems to be using a specific syntax for `vec0`.
                    # Let's assume the original query structure was correct for their sqlite-vec version.
                    # `WHERE r.embedding MATCH json_extract(?, '$') AND k = ?`
                    # The `json_extract` might be needed if `?1` is a JSON string.
                    # `vec0` expects the vector directly.
                    sql_vector_search = """
                        SELECT c.chunk_text, c.source_type, c.source_ref, r.distance
                        FROM rag_embeddings r
                        JOIN rag_chunks c ON r.rowid = c.chunk_id
                        WHERE r.embedding MATCH ? 
                        ORDER BY r.distance
                        LIMIT ? 
                    """ # Using LIMIT for 'k' is more standard for vec0 if k isn't part of MATCH syntax.
                      # The original query `AND k = ?2` might be specific to a version or a different VSS extension.
                      # For `vec0`, you usually pass the query vector and limit results.
                      # The original code `WHERE r.embedding MATCH ?1 AND k = ?2` is unusual.
                      # `vec0` queries are typically like `WHERE vss_search(embedding, query_vector(?1), k_value(?2))`
                      # or `WHERE embedding MATCH ?1 LIMIT ?2`.
                      # Given `MATCH ?1`, `LIMIT ?2` is the most probable correct interpretation for `vec0`.
                    
                    # The original query was:
                    # WHERE r.embedding MATCH ?1 AND k = ?2 ORDER BY r.distance
                    # For `vec0`, `MATCH` takes the query vector. `k` is not part of `MATCH`.
                    # So, we use `LIMIT`.
                    cursor.execute(sql_vector_search, (query_embedding_json, k_results))
                    vector_search_results = [dict(row) for row in cursor.fetchall()]
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
                source_info = f"Source Type: {item['source_type']}, Reference: {item['source_ref']}"
                distance = item.get('distance', 'N/A') # Distance might not always be present depending on VSS
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
Be concise and directly answer the query based on the provided information."""
            
            user_message_for_llm = f"CONTEXT:\n{combined_context_str}\n\nQUERY:\n{query_text}\n\nBased *only* on the CONTEXT provided above, please answer the QUERY."

            logger.debug(f"RAG Query: Combined context for LLM (approx tokens: {current_token_count}):\n{combined_context_str[:500]}...") # Log excerpt
            logger.debug(f"RAG Query: User message for LLM:\n{user_message_for_llm[:500]}...")

            chat_response = openai_client.chat.completions.create(
                model=CHAT_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt_for_llm},
                    {"role": "user", "content": user_message_for_llm}
                ],
                # temperature=0.2 # Consider adding for more factual responses
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