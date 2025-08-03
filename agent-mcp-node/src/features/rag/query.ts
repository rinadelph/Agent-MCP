// RAG query functionality for Agent-MCP Node.js
// Ported from Python features/rag/query.py

import { getDbConnection, isVssLoadable, createDbConnection } from '../../db/connection.js';
import { getOpenAIClient, generateEmbeddings } from '../../external/openai_service.js';
import { 
  CHAT_MODEL, 
  MAX_CONTEXT_TOKENS, 
  EMBEDDING_MODEL, 
  EMBEDDING_DIMENSION,
  MCP_DEBUG 
} from '../../core/config.js';

/**
 * Interface for live context results
 */
interface LiveContextResult {
  context_key: string;
  value: string;
  description?: string;
  last_updated: string;
}

/**
 * Interface for live task results
 */
interface LiveTaskResult {
  task_id: string;
  title: string;
  status: string;
  description?: string;
  updated_at: string;
  priority?: string;
  assigned_to?: string;
  created_by?: string;
  parent_task?: string;
  depends_on_tasks?: string;
  created_at?: string;
}

/**
 * Interface for vector search results
 */
interface VectorSearchResult {
  chunk_text: string;
  source_type: string;
  source_ref: string;
  metadata?: any;
  distance?: number;
}

/**
 * Interface for RAG query results with detailed information
 */
export interface RagQueryResult {
  answer?: string;
  chunks: Array<{
    chunkText: string;
    sourceType: string;
    sourceRef: string;
    metadata?: any;
    distance?: number;
    chunkId?: number;
  }>;
  stats?: {
    liveContextCount: number;
    liveTaskCount: number;
    vectorSearchCount: number;
    totalTokensApprox: number;
    vssAvailable: boolean;
  };
}

/**
 * Interface for query options
 */
export interface RagQueryOptions {
  k?: number;
  includeStats?: boolean;
  model?: string;
  maxTokens?: number;
}

/**
 * Overloaded function for RAG system queries
 */
export async function queryRagSystem(queryText: string): Promise<string>;
export async function queryRagSystem(queryText: string, options: RagQueryOptions): Promise<RagQueryResult>;
export async function queryRagSystem(queryText: string, options?: RagQueryOptions): Promise<string | RagQueryResult> {
  if (options) {
    return queryRagSystemDetailed(queryText, options);
  }
  return queryRagSystemSimple(queryText);
}

/**
 * Processes a natural language query using the RAG system.
 * Fetches relevant context from live data and indexed knowledge,
 * then uses an LLM to synthesize an answer.
 */
async function queryRagSystemSimple(queryText: string): Promise<string> {
  // Get OpenAI client
  const openaiClient = getOpenAIClient();
  if (!openaiClient) {
    console.error('RAG Query: OpenAI client is not available. Cannot process query.');
    return 'RAG Error: OpenAI client not available. Please check server configuration and OpenAI API key.';
  }

  let answer = 'An unexpected error occurred during the RAG query.';

  try {
    const db = getDbConnection();
    
    let liveContextResults: LiveContextResult[] = [];
    let liveTaskResults: LiveTaskResult[] = [];
    let vectorSearchResults: VectorSearchResult[] = [];

    // --- 1. Fetch Live Context (Recently Updated) ---
    try {
      const lastIndexedResult = db.prepare('SELECT meta_value FROM rag_meta WHERE meta_key = ?')
        .get('last_indexed_context') as { meta_value: string } | undefined;
      
      const lastIndexedContextTime = lastIndexedResult?.meta_value || '1970-01-01T00:00:00Z';

      const contextRows = db.prepare(`
        SELECT context_key, value, description, last_updated
        FROM project_context
        WHERE last_updated > ?
        ORDER BY last_updated DESC
        LIMIT 5
      `).all(lastIndexedContextTime);

      liveContextResults = contextRows as LiveContextResult[];
    } catch (error) {
      console.warn('RAG Query: Failed to fetch live project context:', error);
    }

    // --- 2. Fetch Live Tasks (Keyword Search) ---
    try {
      const queryKeywords = queryText.split(' ')
        .map(word => word.trim().toLowerCase())
        .filter(word => word.length > 2)
        .map(word => `%${word}%`);

      if (queryKeywords.length > 0) {
        // Build LIKE clauses for title and description
        const conditions: string[] = [];
        const sqlParams: string[] = [];
        
        for (const keyword of queryKeywords) {
          conditions.push('LOWER(title) LIKE ?');
          sqlParams.push(keyword);
          conditions.push('LOWER(description) LIKE ?');
          sqlParams.push(keyword);
        }

        if (conditions.length > 0) {
          const whereClause = conditions.join(' OR ');
          const taskQuerySql = `
            SELECT task_id, title, status, description, updated_at
            FROM tasks
            WHERE ${whereClause}
            ORDER BY updated_at DESC
            LIMIT 5
          `;
          
          const taskRows = db.prepare(taskQuerySql).all(...sqlParams);
          liveTaskResults = taskRows as LiveTaskResult[];
        }
      }
    } catch (error) {
      console.warn('RAG Query: Failed to fetch live tasks based on query keywords:', error);
    }

    // --- 3. Perform Vector Search (Indexed Knowledge) ---
    if (isVssLoadable()) {
      // Use a fresh connection for vector search to ensure sqlite-vec is loaded
      const vectorDb = createDbConnection();
      try {
        // Check if rag_embeddings table exists
        const tableCheck = vectorDb.prepare(`
          SELECT name FROM sqlite_master 
          WHERE type='table' AND name='rag_embeddings'
        `).get();

        if (tableCheck) {
          // Generate embedding for query
          const embeddings = await generateEmbeddings([queryText], EMBEDDING_MODEL, EMBEDDING_DIMENSION);
          const queryEmbedding = embeddings[0];

          if (queryEmbedding) {
            const queryEmbeddingJson = JSON.stringify(queryEmbedding);
            const kResults = 13; // Optimized based on recent RAG research

            const vectorSearchSql = `
              SELECT c.chunk_text, c.source_type, c.source_ref, c.metadata, r.distance
              FROM rag_embeddings r
              JOIN rag_chunks c ON r.rowid = c.chunk_id
              WHERE r.embedding MATCH ? AND k = ?
              ORDER BY r.distance
            `;

            const rawResults = vectorDb.prepare(vectorSearchSql).all(queryEmbeddingJson, kResults);

            // Process results to parse metadata
            for (const row of rawResults) {
              const result = row as any;
              // Parse metadata JSON if present
              if (result.metadata) {
                try {
                  result.metadata = JSON.parse(result.metadata);
                } catch (error) {
                  result.metadata = null;
                }
              }
              vectorSearchResults.push(result);
            }
          }
        } else {
          console.warn("RAG Query: 'rag_embeddings' table not found. Skipping vector search.");
        }
      } catch (error) {
        console.error('RAG Query: Error during vector search:', error);
      } finally {
        vectorDb.close();
      }
    } else {
      console.warn('RAG Query: Vector search (sqlite-vec) is not available. Skipping vector search.');
    }

    // --- 4. Combine Contexts for LLM ---
    const contextParts: string[] = [];
    let currentTokenCount = 0; // Approximate token count

    // Add Live Context
    if (liveContextResults.length > 0) {
      contextParts.push('--- Recently Updated Project Context (Live) ---');
      for (const item of liveContextResults) {
        const entryText = `Key: ${item.context_key}\nValue: ${item.value}\nDescription: ${item.description || 'N/A'}\n(Updated: ${item.last_updated})\n`;
        const entryTokens = entryText.split(' ').length; // Approximation
        if (currentTokenCount + entryTokens < MAX_CONTEXT_TOKENS) {
          contextParts.push(entryText);
          currentTokenCount += entryTokens;
        } else {
          break;
        }
      }
      contextParts.push('---------------------------------------------');
    }

    // Add Live Tasks
    if (liveTaskResults.length > 0) {
      contextParts.push('--- Potentially Relevant Tasks (Live) ---');
      for (const task of liveTaskResults) {
        const entryText = `Task ID: ${task.task_id}\nTitle: ${task.title}\nStatus: ${task.status}\nDescription: ${task.description || 'N/A'}\n(Updated: ${task.updated_at})\n`;
        const entryTokens = entryText.split(' ').length;
        if (currentTokenCount + entryTokens < MAX_CONTEXT_TOKENS) {
          contextParts.push(entryText);
          currentTokenCount += entryTokens;
        } else {
          break;
        }
      }
      contextParts.push('---------------------------------------');
    }

    // Add Indexed Knowledge (Vector Search Results)
    if (vectorSearchResults.length > 0) {
      contextParts.push('--- Indexed Project Knowledge (Vector Search Results) ---');
      for (let i = 0; i < vectorSearchResults.length; i++) {
        const item = vectorSearchResults[i];
        if (!item) continue;

        const chunkText = item.chunk_text;
        const sourceType = item.source_type;
        const sourceRef = item.source_ref;
        const metadata = item.metadata || {};
        const distance = item.distance || 'N/A';

        // Enhanced source info with metadata
        let sourceInfo = `Source Type: ${sourceType}, Reference: ${sourceRef}`;

        // Add code-specific metadata if available
        if (metadata && ['code', 'code_summary'].includes(sourceType)) {
          if (metadata.language) {
            sourceInfo += `, Language: ${metadata.language}`;
          }
          if (metadata.section_type) {
            sourceInfo += `, Section: ${metadata.section_type}`;
          }
          if (metadata.entities && Array.isArray(metadata.entities)) {
            const entityNames = metadata.entities
              .map((e: any) => e.name || '')
              .filter((name: string) => name);
            if (entityNames.length > 0) {
              sourceInfo += `, Contains: ${entityNames.slice(0, 3).join(', ')}`;
              if (entityNames.length > 3) {
                sourceInfo += ` (+${entityNames.length - 3} more)`;
              }
            }
          }
        }

        const entryText = `Retrieved Chunk ${i + 1} (Similarity/Distance: ${distance}):\n${sourceInfo}\nContent:\n${chunkText}\n`;
        const chunkTokens = entryText.split(' ').length;
        if (currentTokenCount + chunkTokens < MAX_CONTEXT_TOKENS) {
          contextParts.push(entryText);
          currentTokenCount += chunkTokens;
        } else {
          contextParts.push('--- [Indexed knowledge truncated due to token limit] ---');
          break;
        }
      }
      contextParts.push('-------------------------------------------------------');
    }

    if (contextParts.length === 0) {
      if (MCP_DEBUG) {
        console.log(`RAG Query: No relevant information found for query: '${queryText}'`);
      }
      answer = 'No relevant information found in the project knowledge base or live data for your query.';
    } else {
      const combinedContextStr = contextParts.join('\n\n');

      // --- 5. Call Chat Completion API ---
      const systemPromptForLlm = `You are an AI assistant answering questions about a software project. 
Use the provided context, which may include recently updated live data (like project context keys or tasks) and information retrieved from an indexed knowledge base (like documentation or code summaries), to answer the user's query. 
Prioritize information from the 'Live' sections if available and relevant for time-sensitive data. 
Answer using *only* the information given in the context. If the context doesn't contain the answer, state that clearly.

Be VERBOSE and comprehensive in your responses. It's better to give too much context than too little. 
When answering, please also suggest additional context entries and queries that might be helpful for understanding this topic better.
For example, suggest related files to examine, related project context keys to check, or follow-up questions that could provide more insight.
Always err on the side of providing more detailed explanations and comprehensive information rather than brief responses.`;

      const userMessageForLlm = `CONTEXT:\n${combinedContextStr}\n\nQUERY:\n${queryText}\n\nBased *only* on the CONTEXT provided above, please answer the QUERY.`;

      if (MCP_DEBUG) {
        console.log(`RAG Query: Combined context for LLM (approx tokens: ${currentTokenCount}):\n${combinedContextStr.substring(0, 500)}...`);
        console.log(`RAG Query: User message for LLM:\n${userMessageForLlm.substring(0, 500)}...`);
      }

      const chatResponse = await openaiClient.chat.completions.create({
        model: CHAT_MODEL,
        messages: [
          { role: 'system', content: systemPromptForLlm },
          { role: 'user', content: userMessageForLlm }
        ],
        temperature: 0.4 // Increased for more diverse context discovery while maintaining accuracy
      });

      answer = chatResponse.choices[0]?.message?.content || 'No response generated';
    }

  } catch (error: any) {
    console.error('RAG Query: Error during query processing:', error);
    if (error.name === 'APIError') {
      answer = `Error communicating with OpenAI: ${error.message}`;
    } else if (error.code && typeof error.code === 'string') {
      answer = `Error querying RAG database: ${error.message}`;
    } else {
      answer = `An unexpected error occurred during the RAG query: ${error.message}`;
    }
  }

  return answer;
}

/**
 * Detailed RAG query that returns statistics and chunks
 */
async function queryRagSystemDetailed(queryText: string, options: RagQueryOptions): Promise<RagQueryResult> {
  const result: RagQueryResult = {
    chunks: [],
    stats: {
      liveContextCount: 0,
      liveTaskCount: 0,
      vectorSearchCount: 0,
      totalTokensApprox: 0,
      vssAvailable: isVssLoadable()
    }
  };

  try {
    const db = getDbConnection();
    
    let liveContextResults: LiveContextResult[] = [];
    let liveTaskResults: LiveTaskResult[] = [];
    let vectorSearchResults: VectorSearchResult[] = [];

    // --- 1. Fetch Live Context (Recently Updated) ---
    try {
      const lastIndexedResult = db.prepare('SELECT meta_value FROM rag_meta WHERE meta_key = ?')
        .get('last_indexed_context') as { meta_value: string } | undefined;
      
      const lastIndexedContextTime = lastIndexedResult?.meta_value || '1970-01-01T00:00:00Z';

      const contextRows = db.prepare(`
        SELECT context_key, value, description, last_updated
        FROM project_context
        WHERE last_updated > ?
        ORDER BY last_updated DESC
        LIMIT 5
      `).all(lastIndexedContextTime);

      liveContextResults = contextRows as LiveContextResult[];
      if (result.stats) {
        result.stats.liveContextCount = liveContextResults.length;
      }
    } catch (error) {
      console.warn('RAG Query: Failed to fetch live project context:', error);
    }

    // --- 2. Fetch Live Tasks (Keyword Search) ---
    try {
      const queryKeywords = queryText.split(' ')
        .map(word => word.trim().toLowerCase())
        .filter(word => word.length > 2)
        .map(word => `%${word}%`);

      if (queryKeywords.length > 0) {
        const conditions: string[] = [];
        const sqlParams: string[] = [];
        
        for (const keyword of queryKeywords) {
          conditions.push('LOWER(title) LIKE ?');
          sqlParams.push(keyword);
          conditions.push('LOWER(description) LIKE ?');
          sqlParams.push(keyword);
        }

        if (conditions.length > 0) {
          const whereClause = conditions.join(' OR ');
          const taskQuerySql = `
            SELECT task_id, title, status, description, updated_at
            FROM tasks
            WHERE ${whereClause}
            ORDER BY updated_at DESC
            LIMIT 5
          `;
          
          const taskRows = db.prepare(taskQuerySql).all(...sqlParams);
          liveTaskResults = taskRows as LiveTaskResult[];
          if (result.stats) {
            result.stats.liveTaskCount = liveTaskResults.length;
          }
        }
      }
    } catch (error) {
      console.warn('RAG Query: Failed to fetch live tasks based on query keywords:', error);
    }

    // --- 3. Perform Vector Search (Indexed Knowledge) ---
    if (isVssLoadable()) {
      const vectorDb = createDbConnection();
      try {
        const tableCheck = vectorDb.prepare(`
          SELECT name FROM sqlite_master 
          WHERE type='table' AND name='rag_embeddings'
        `).get();

        if (tableCheck) {
          const embeddings = await generateEmbeddings([queryText], EMBEDDING_MODEL, EMBEDDING_DIMENSION);
          const queryEmbedding = embeddings[0];

          if (queryEmbedding) {
            const queryEmbeddingJson = JSON.stringify(queryEmbedding);
            const kResults = options.k || 13;

            const vectorSearchSql = `
              SELECT c.chunk_text, c.source_type, c.source_ref, c.metadata, c.chunk_id, r.distance
              FROM rag_embeddings r
              JOIN rag_chunks c ON r.rowid = c.chunk_id
              WHERE r.embedding MATCH ? AND k = ?
              ORDER BY r.distance
            `;

            const rawResults = vectorDb.prepare(vectorSearchSql).all(queryEmbeddingJson, kResults);

            for (const row of rawResults) {
              const result_row = row as any;
              let metadata = null;
              if (result_row.metadata) {
                try {
                  metadata = JSON.parse(result_row.metadata);
                } catch (error) {
                  metadata = null;
                }
              }

              result.chunks.push({
                chunkText: result_row.chunk_text,
                sourceType: result_row.source_type,
                sourceRef: result_row.source_ref,
                metadata: metadata,
                distance: result_row.distance,
                chunkId: result_row.chunk_id
              });
            }

            if (result.stats) {
              result.stats.vectorSearchCount = result.chunks.length;
            }
          }
        }
      } catch (error) {
        console.error('RAG Query: Error during vector search:', error);
      } finally {
        vectorDb.close();
      }
    }

    // Calculate approximate token count
    if (result.stats) {
      const contextText = liveContextResults.map(c => c.value || '').join(' ');
      const taskText = liveTaskResults.map(t => `${t.title} ${t.description || ''}`).join(' ');
      const chunkText = result.chunks.map(c => c.chunkText).join(' ');
      
      result.stats.totalTokensApprox = Math.floor((contextText + taskText + chunkText).split(' ').length * 0.75);
    }

    if (options.includeStats !== false) {
      return result;
    } else {
      // Remove stats if not requested
      delete result.stats;
      return result;
    }

  } catch (error) {
    console.error('RAG Query: Error in detailed query:', error);
    return result;
  }
}

/**
 * Processes a query using the RAG system with a specific OpenAI model.
 * This is useful for task analysis with cheaper models while keeping
 * main RAG queries on the premium model.
 */
export async function queryRagSystemWithModel(
  queryText: string, 
  modelName: string, 
  maxTokens?: number
): Promise<string> {
  // Get OpenAI client
  const openaiClient = getOpenAIClient();
  if (!openaiClient) {
    console.error('RAG Query: OpenAI client is not available. Cannot process query.');
    return 'RAG Error: OpenAI client not available. Please check server configuration and OpenAI API key.';
  }

  // Use provided max_tokens or default to the configured value
  const contextLimit = maxTokens || MAX_CONTEXT_TOKENS;
  let answer = 'An unexpected error occurred during the RAG query.';

  try {
    const db = getDbConnection();
    
    let liveContextResults: LiveContextResult[] = [];
    let liveTaskResults: LiveTaskResult[] = [];
    let vectorSearchResults: VectorSearchResult[] = [];

    // Get live context (same as regular RAG)
    const contextRows = db.prepare(`
      SELECT context_key, value, description, last_updated 
      FROM project_context 
      ORDER BY last_updated DESC
    `).all();
    liveContextResults = contextRows as LiveContextResult[];

    // Get live tasks (same as regular RAG)
    const taskRows = db.prepare(`
      SELECT task_id, title, description, status, created_by, assigned_to, 
             priority, parent_task, depends_on_tasks, created_at, updated_at 
      FROM tasks 
      WHERE status IN ('pending', 'in_progress') 
      ORDER BY updated_at DESC
    `).all();
    liveTaskResults = taskRows as LiveTaskResult[];

    // Get vector search results if VSS is available
    if (isVssLoadable()) {
      try {
        // Check if rag_embeddings table exists
        const tableCheck = db.prepare(`
          SELECT name FROM sqlite_master 
          WHERE type='table' AND name='rag_embeddings'
        `).get();

        if (tableCheck) {
          // Embed the query
          const embeddings = await generateEmbeddings([queryText], EMBEDDING_MODEL, EMBEDDING_DIMENSION);
          const queryEmbedding = embeddings[0];

          if (queryEmbedding) {
            const queryEmbeddingJson = JSON.stringify(queryEmbedding);
            const kResults = 13; // Optimized based on recent RAG research

            const vectorSearchSql = `
              SELECT c.chunk_text, c.source_type, c.source_ref, c.metadata, r.distance
              FROM rag_embeddings r
              JOIN rag_chunks c ON r.rowid = c.chunk_id
              WHERE r.embedding MATCH ? AND k = ?
              ORDER BY r.distance
            `;

            const rawResults = db.prepare(vectorSearchSql).all(queryEmbeddingJson, kResults);

            // Process results to parse metadata
            for (const row of rawResults) {
              const result = row as any;
              // Parse metadata JSON if present
              if (result.metadata) {
                try {
                  result.metadata = JSON.parse(result.metadata);
                } catch (error) {
                  result.metadata = null;
                }
              }
              vectorSearchResults.push(result);
            }
          }
        } else {
          console.warn("RAG Query: 'rag_embeddings' table not found. Skipping vector search.");
        }
      } catch (error) {
        console.error('RAG Query: Error during vector search:', error);
      }
    }

    // Build context (same structure as regular RAG)
    const contextParts: string[] = [];
    let currentTokenCount = 0;

    // Include live context
    if (liveContextResults.length > 0) {
      contextParts.push('=== Live Project Context ===');
      for (const item of liveContextResults) {
        const entryText = `Key: ${item.context_key}\nDescription: ${item.description}\nValue: ${item.value}\nLast Updated: ${item.last_updated}\n`;
        const chunkTokens = entryText.split(' ').length;
        if (currentTokenCount + chunkTokens < contextLimit) {
          contextParts.push(entryText);
          currentTokenCount += chunkTokens;
        } else {
          contextParts.push('--- [Live context truncated due to token limit] ---');
          break;
        }
      }
    }

    // Include live tasks
    if (liveTaskResults.length > 0) {
      contextParts.push('\n=== Live Task Information ===');
      for (const item of liveTaskResults) {
        let entryText = `Task ID: ${item.task_id}\nTitle: ${item.title}\nDescription: ${item.description}\nStatus: ${item.status}\n`;
        entryText += `Priority: ${item.priority}\nAssigned To: ${item.assigned_to}\nCreated By: ${item.created_by}\n`;
        entryText += `Parent Task: ${item.parent_task}\nDependencies: ${item.depends_on_tasks}\n`;
        entryText += `Created: ${item.created_at}\nUpdated: ${item.updated_at}\n`;
        
        const chunkTokens = entryText.split(' ').length;
        if (currentTokenCount + chunkTokens < contextLimit) {
          contextParts.push(entryText);
          currentTokenCount += chunkTokens;
        } else {
          contextParts.push('--- [Live tasks truncated due to token limit] ---');
          break;
        }
      }
    }

    // Include vector search results
    if (vectorSearchResults.length > 0) {
      contextParts.push('\n=== Retrieved from Indexed Knowledge ===');
      for (let i = 0; i < vectorSearchResults.length; i++) {
        const item = vectorSearchResults[i];
        if (!item) continue;

        const chunkText = item.chunk_text;
        const sourceType = item.source_type;
        const sourceRef = item.source_ref;
        const metadata = item.metadata || {};
        const distance = item.distance || 'N/A';

        // Enhanced source info with metadata
        let sourceInfo = `Source Type: ${sourceType}, Reference: ${sourceRef}`;

        // Add code-specific metadata if available
        if (metadata && ['code', 'code_summary'].includes(sourceType)) {
          if (metadata.language) {
            sourceInfo += `, Language: ${metadata.language}`;
          }
          if (metadata.section_type) {
            sourceInfo += `, Section: ${metadata.section_type}`;
          }
          if (metadata.entities && Array.isArray(metadata.entities)) {
            const entityNames = metadata.entities
              .map((e: any) => e.name || '')
              .filter((name: string) => name);
            if (entityNames.length > 0) {
              sourceInfo += `, Contains: ${entityNames.slice(0, 3).join(', ')}`;
              if (entityNames.length > 3) {
                sourceInfo += ` (+${entityNames.length - 3} more)`;
              }
            }
          }
        }

        const entryText = `Retrieved Chunk ${i + 1} (Similarity/Distance: ${distance}):\n${sourceInfo}\nContent:\n${chunkText}\n`;
        const chunkTokens = entryText.split(' ').length;
        if (currentTokenCount + chunkTokens < contextLimit) {
          contextParts.push(entryText);
          currentTokenCount += chunkTokens;
        } else {
          contextParts.push('--- [Indexed knowledge truncated due to token limit] ---');
          break;
        }
      }
    }

    if (contextParts.length === 0) {
      if (MCP_DEBUG) {
        console.log(`RAG Query: No relevant information found for query: '${queryText}'`);
      }
      answer = 'No relevant information found in the project knowledge base or live data for your query.';
    } else {
      const combinedContextStr = contextParts.join('\n\n');

      // Call Chat Completion API with specified model
      const systemPromptForLlm = `You are an AI assistant specializing in task hierarchy analysis and project structure optimization. 
You must CRITICALLY THINK about task placement, dependencies, and hierarchical relationships.
Use the provided context to make intelligent recommendations about task organization.
Be strict about the single root task rule and logical task relationships.

Be VERBOSE and comprehensive in your analysis. It's better to give too much context than too little.
When making recommendations, suggest additional context entries and queries that might be helpful for understanding task relationships better.
Consider suggesting related files to examine, project context keys to check, or follow-up questions for deeper task analysis.
Provide detailed explanations for your reasoning and comprehensive information rather than brief responses.
Answer in the exact JSON format requested, but include thorough explanations in your reasoning sections.`;

      const userMessageForLlm = `CONTEXT:\n${combinedContextStr}\n\nQUERY:\n${queryText}\n\nBased on the CONTEXT provided above, please answer the QUERY.`;

      if (MCP_DEBUG) {
        console.log(`Task Analysis Query: Using model ${modelName} with ${contextLimit} token limit`);
      }

      // Use the specified model for this query
      const chatResponse = await openaiClient.chat.completions.create({
        model: modelName,
        messages: [
          { role: 'system', content: systemPromptForLlm },
          { role: 'user', content: userMessageForLlm }
        ],
        temperature: 0.4 // Increased for more diverse analysis while maintaining JSON consistency
      });

      answer = chatResponse.choices[0]?.message?.content || 'No response generated';
    }

  } catch (error: any) {
    console.error(`RAG Query with model ${modelName}: Error:`, error);
    answer = `Error during RAG query with ${modelName}: ${error.message}`;
  }

  return answer;
}

console.log('✅ RAG query functionality loaded');