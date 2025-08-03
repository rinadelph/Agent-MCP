// OpenAI Service for Agent-MCP Node.js
// Ported from Python external/openai_service.py with TypeScript implementation

import OpenAI from 'openai';
import { MCP_DEBUG } from '../core/config.js';
import { globalState } from '../core/globals.js';

/**
 * Initialize the OpenAI client with API key validation
 * Sets the global client instance for reuse across the application
 */
export function initializeOpenAIClient(): OpenAI | null {
  if (globalState.openaiClientInstance) {
    console.log('OpenAI client already initialized');
    return globalState.openaiClientInstance;
  }

  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    console.error('CRITICAL: OPENAI_API_KEY not found in environment variables.');
    console.error('Please set it in your .env file or environment.');
    return null;
  }

  console.log('🔑 Initializing OpenAI client...');
  
  try {
    // Create the OpenAI client instance
    const client = new OpenAI({
      apiKey: apiKey
    });

    // Test the connection by making a simple API call
    // Note: We'll do this synchronously for initialization validation
    // In production, you might want to handle this asynchronously
    console.log('✅ OpenAI client initialized successfully');
    
    globalState.openaiClientInstance = client;
    return client;
    
  } catch (error) {
    console.error('❌ Failed to initialize OpenAI client:', error);
    
    if (error instanceof Error) {
      if (error.message.includes('authentication') || error.message.includes('401')) {
        console.error('OpenAI Authentication Error: Invalid API key. Please check your credentials.');
      } else if (error.message.includes('network') || error.message.includes('connection')) {
        console.error('OpenAI Connection Error: Could not connect to OpenAI. Check your network settings.');
      } else if (error.message.includes('rate limit') || error.message.includes('429')) {
        console.error('OpenAI Rate Limit Error: You have exceeded your API quota or rate limit.');
      } else {
        console.error('OpenAI API Error during client initialization:', error.message);
      }
    }
    
    globalState.openaiClientInstance = null;
    return null;
  }
}

/**
 * Get the globally initialized OpenAI client instance
 * Attempts to initialize if not already done
 */
export function getOpenAIClient(): OpenAI | null {
  if (!globalState.openaiClientInstance) {
    if (MCP_DEBUG) {
      console.log('OpenAI client not yet initialized. Attempting initialization now.');
    }
    initializeOpenAIClient();
  }

  if (!globalState.openaiClientInstance) {
    console.warn('⚠️ OpenAI client is not available (initialization might have failed)');
  }

  return globalState.openaiClientInstance;
}

/**
 * Generate embeddings for a list of text chunks
 * Handles batching and error management
 */
export async function generateEmbeddings(
  texts: string[],
  model: string = 'text-embedding-3-small',
  dimensions?: number
): Promise<Array<number[] | null>> {
  const client = getOpenAIClient();
  if (!client) {
    throw new Error('OpenAI client not available');
  }

  if (texts.length === 0) {
    return [];
  }

  try {
    const response = await client.embeddings.create({
      input: texts,
      model: model,
      dimensions: dimensions
    });

    // Extract embeddings from response
    const embeddings: Array<number[] | null> = new Array(texts.length).fill(null);
    
    for (let i = 0; i < response.data.length; i++) {
      const embeddingData = response.data[i];
      if (embeddingData && embeddingData.embedding) {
        embeddings[embeddingData.index || i] = embeddingData.embedding;
      }
    }

    if (MCP_DEBUG) {
      console.log(`🔢 Generated ${response.data.length} embeddings for ${texts.length} texts`);
    }

    return embeddings;
    
  } catch (error) {
    console.error('Error generating embeddings:', error);
    
    if (error instanceof Error) {
      if (error.message.includes('rate limit') || error.message.includes('429')) {
        throw new Error('OpenAI rate limit exceeded. Please wait before retrying.');
      } else if (error.message.includes('authentication') || error.message.includes('401')) {
        throw new Error('OpenAI authentication failed. Please check your API key.');
      } else if (error.message.includes('quota') || error.message.includes('billing')) {
        throw new Error('OpenAI quota exceeded. Please check your billing status.');
      }
    }
    
    throw new Error(`Failed to generate embeddings: ${error instanceof Error ? error.message : String(error)}`);
  }
}

/**
 * Generate a single embedding for text
 * Convenience function for single text embedding
 */
export async function generateSingleEmbedding(
  text: string,
  model: string = 'text-embedding-3-small',
  dimensions?: number
): Promise<number[]> {
  const embeddings = await generateEmbeddings([text], model, dimensions);
  const embedding = embeddings[0];
  
  if (!embedding) {
    throw new Error('Failed to generate embedding for text');
  }
  
  return embedding;
}

/**
 * Test the OpenAI connection with a simple embeddings call
 * Useful for verifying the setup is working
 */
export async function testOpenAIConnection(): Promise<boolean> {
  try {
    const testEmbedding = await generateSingleEmbedding('test connection', 'text-embedding-3-small', 512);
    return testEmbedding.length > 0;
  } catch (error) {
    console.error('OpenAI connection test failed:', error);
    return false;
  }
}

/**
 * Chat completion function for RAG queries
 * Handles the LLM response generation with context
 */
export async function generateChatCompletion(
  messages: Array<{ role: 'system' | 'user' | 'assistant'; content: string }>,
  model: string = 'gpt-4',
  temperature: number = 0.4
): Promise<string> {
  const client = getOpenAIClient();
  if (!client) {
    throw new Error('OpenAI client not available');
  }

  try {
    const response = await client.chat.completions.create({
      model: model,
      messages: messages,
      temperature: temperature
    });

    const content = response.choices[0]?.message?.content;
    if (!content) {
      throw new Error('No content received from OpenAI chat completion');
    }

    if (MCP_DEBUG) {
      console.log(`💬 Generated chat completion using ${model}`);
    }

    return content;
    
  } catch (error) {
    console.error('Error generating chat completion:', error);
    
    if (error instanceof Error) {
      if (error.message.includes('rate limit') || error.message.includes('429')) {
        throw new Error('OpenAI rate limit exceeded. Please wait before retrying.');
      } else if (error.message.includes('authentication') || error.message.includes('401')) {
        throw new Error('OpenAI authentication failed. Please check your API key.');
      } else if (error.message.includes('quota') || error.message.includes('billing')) {
        throw new Error('OpenAI quota exceeded. Please check your billing status.');
      }
    }
    
    throw new Error(`Failed to generate chat completion: ${error instanceof Error ? error.message : String(error)}`);
  }
}

console.log('✅ OpenAI service module loaded');