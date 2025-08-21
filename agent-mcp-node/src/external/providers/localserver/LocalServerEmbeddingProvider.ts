// Local Embedding Server Provider
// Connects to OpenAI-compatible embedding server running locally

import { BaseEmbeddingProvider } from '../BaseEmbeddingProvider.js';
import { PROVIDER_CONFIG, MCP_DEBUG } from '../../../core/config.js';

/**
 * Local Embedding Server Provider Implementation
 * Connects to local OpenAI-compatible embedding server (e.g., on port 4127)
 * 
 * Configuration:
 * Set LOCAL_EMBEDDING_URL=http://localhost:4127
 * Set LOCAL_EMBEDDING_MODEL=qwen2.5:0.5b
 */
export class LocalServerEmbeddingProvider extends BaseEmbeddingProvider {
  private baseUrl: string;
  private model: string;
  private dimensions: number = 896; // qwen2.5:0.5b uses 896 dimensions
  
  constructor() {
    super();
    this.baseUrl = process.env.LOCAL_EMBEDDING_URL || 'http://localhost:4127';
    this.model = process.env.LOCAL_EMBEDDING_MODEL || 'qwen2.5:0.5b';
    
    // Update dimensions based on model
    if (this.model.includes('qwen')) {
      this.dimensions = 896;
    }
  }
  
  protected getProviderType(): string {
    return 'localserver';
  }
  
  protected getDefaultModel(): string {
    return this.model;
  }
  
  protected getDefaultMaxBatchSize(): number {
    return 100; // Adjust based on your server's capabilities
  }
  
  protected isLocalProvider(): boolean {
    return true;
  }
  
  async isAvailable(): Promise<boolean> {
    try {
      // Check if the server is running
      const response = await fetch(`${this.baseUrl}/v1/models`, {
        signal: AbortSignal.timeout(5000)
      });
      
      if (!response.ok) {
        console.warn(`Local embedding server returned status ${response.status}`);
        return false;
      }
      
      const data = await response.json();
      
      // Check if our model is available
      const modelAvailable = data.data?.some((m: any) => 
        m.id === this.model || m.id.includes(this.model.split(':')[0])
      );
      
      if (!modelAvailable && MCP_DEBUG) {
        console.warn(`Model ${this.model} not found in available models`);
        console.log('Available models:', data.data?.map((m: any) => m.id));
      }
      
      return true; // Server is available even if specific model isn't listed
    } catch (error) {
      if (MCP_DEBUG) {
        console.warn('Local embedding server not available:', error);
      }
      return false;
    }
  }
  
  async warmUp(): Promise<void> {
    // Warm up the model with a test embedding
    console.log(`🔥 Warming up local embedding server with ${this.model}...`);
    try {
      await this.generateEmbeddings(['warmup test']);
      console.log('✅ Local embedding server warmed up');
    } catch (error) {
      console.warn('Failed to warm up local embedding server:', error);
    }
  }
  
  protected async generateEmbeddingsInternal(texts: string[]): Promise<number[][]> {
    try {
      const response = await fetch(`${this.baseUrl}/v1/embeddings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          input: texts,
          model: this.model
        })
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Embedding server error ${response.status}: ${errorText}`);
      }
      
      const data = await response.json();
      
      // Extract embeddings from OpenAI-compatible response format
      const embeddings: number[][] = [];
      
      if (data.data && Array.isArray(data.data)) {
        for (const item of data.data) {
          if (item.embedding) {
            embeddings.push(item.embedding);
          }
        }
      }
      
      if (embeddings.length !== texts.length) {
        throw new Error(`Expected ${texts.length} embeddings but got ${embeddings.length}`);
      }
      
      if (MCP_DEBUG) {
        console.log(`✅ Generated ${embeddings.length} embeddings via local server`);
        console.log(`   Model: ${this.model}, Dimensions: ${embeddings[0]?.length || 0}`);
      }
      
      return embeddings;
      
    } catch (error) {
      console.error('Failed to generate embeddings from local server:', error);
      throw error;
    }
  }
  
  getDimensions(): number {
    return this.dimensions;
  }
  
  estimateCost(tokenCount: number): number {
    return 0; // Local server is free
  }
}

console.log('✅ Local embedding server provider loaded');