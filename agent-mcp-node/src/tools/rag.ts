// RAG tools for Agent-MCP Node.js
// Provides tools for querying the project's knowledge base using vector search

import { z } from 'zod';
import { registerTool } from './registry.js';
import { queryRagSystem, RagQueryOptions } from '../features/rag/query.js';
import { getVectorSearchStats } from '../features/rag/vectorSearch.js';
import { MCP_DEBUG } from '../core/config.js';

/**
 * Tool for querying the project's RAG knowledge base
 * Uses vector search and live data to provide contextual answers
 */
registerTool(
  'ask_project_rag',
  'Query the project\'s knowledge base using RAG (Retrieval Augmented Generation). Searches indexed code, documentation, tasks, and context for relevant information.',
  z.object({
    query: z.string().min(1).describe('Natural language query to search for in the project knowledge base')
  }),
  async (args, context) => {
    try {
      const { query } = args;

      if (MCP_DEBUG) {
        console.log(`🔍 RAG Query from ${context.agentId}: "${query.substring(0, 100)}..."`);
      }

      // Use the standard RAG query (like Python implementation)
      const answer = await queryRagSystem(query);

      return {
        content: [
          {
            type: 'text' as const,
            text: answer
          }
        ],
        isError: false
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error('Error in ask_project_rag tool:', error);

      return {
        content: [
          {
            type: 'text' as const,
            text: `❌ RAG query failed: ${errorMessage}\n\nThis could be due to:\n- Vector search not available (sqlite-vec extension)\n- OpenAI API issues\n- Database connectivity problems\n\nPlease check the server logs for more details.`
          }
        ],
        isError: true
      };
    }
  }
);

/**
 * Tool for getting RAG system status and statistics
 */
registerTool(
  'get_rag_status',
  'Get the current status and statistics of the RAG (Retrieval Augmented Generation) system',
  z.object({}),
  async (args, context) => {
    try {
      const stats = getVectorSearchStats();
      
      const statusText = `# RAG System Status

## Vector Search
- **Available**: ${stats.available ? '✅ Yes' : '❌ No'}
- **Table Exists**: ${stats.tableExists ? '✅ Yes' : '❌ No'}

## Indexed Content
- **Chunks**: ${stats.chunkCount.toLocaleString()} text chunks
- **Embeddings**: ${stats.embeddingCount.toLocaleString()} vector embeddings
- **Coverage**: ${stats.chunkCount > 0 ? ((stats.embeddingCount / stats.chunkCount) * 100).toFixed(1) + '%' : '0%'} of chunks have embeddings

## System Health
${stats.available && stats.tableExists && stats.embeddingCount > 0 
  ? '🟢 **Healthy** - RAG system is fully operational' 
  : stats.available && stats.tableExists 
    ? '🟡 **Partial** - System ready but no content indexed yet'
    : '🔴 **Unavailable** - Vector search extension not loaded'
}

${!stats.available ? '\n⚠️  **Note**: sqlite-vec extension is not available. Vector search functionality is disabled.' : ''}
${stats.available && stats.chunkCount === 0 ? '\n💡 **Tip**: No content has been indexed yet. Use indexing tools to populate the knowledge base.' : ''}
`;

      return {
        content: [
          {
            type: 'text' as const,
            text: statusText
          }
        ],
        isError: false
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error('Error getting RAG status:', error);

      return {
        content: [
          {
            type: 'text' as const,
            text: `❌ Failed to get RAG status: ${errorMessage}`
          }
        ],
        isError: true
      };
    }
  }
);

console.log('✅ RAG tools loaded');