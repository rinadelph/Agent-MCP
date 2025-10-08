// Ollama Embedding Provider
// Users should implement this provider to use Ollama local embeddings

import { BaseEmbeddingProvider } from '../BaseEmbeddingProvider.js';
import { PROVIDER_CONFIG } from '../../../core/config.js';

/**
 * Ollama Embedding Provider Implementation
 * Uses Ollama for local embedding generation
 * 
 * To implement:
 * 1. Install Ollama: https://ollama.ai
 * 2. Pull embedding model: ollama pull nomic-embed-text
 * 3. Implement generateEmbeddingsInternal method
 */
export class OllamaEmbeddingProvider extends BaseEmbeddingProvider {
  protected getProviderType(): string {
    return 'ollama';
  }
  
  protected getDefaultModel(): string {
    return PROVIDER_CONFIG.OLLAMA_MODEL || 'nomic-embed-text';
  }
  
  protected getDefaultMaxBatchSize(): number {
    return 50; // Adjust based on local memory
  }
  
  protected isLocalProvider(): boolean {
    return true;
  }
  
  async isAvailable(): Promise<boolean> {
    try {
      // Check if Ollama is running
      const response = await fetch(`${PROVIDER_CONFIG.OLLAMA_BASE_URL}/api/tags`, {
        signal: AbortSignal.timeout(5000)
      });
      
      if (!response.ok) {
        return false;
      }
      
      // Check if the model is available
      const data = await response.json();
      const modelAvailable = data.models?.some((m: any) => 
        m.name === this.getModel() || 
        m.name.startsWith(this.getModel() + ':')
      );
      
      if (!modelAvailable) {
        console.warn(`Ollama model ${this.getModel()} not found. Pull it with: ollama pull ${this.getModel()}`);
        return false;
      }
      
      return true;
    } catch (error) {
      console.warn('Ollama not available:', error);
      return false;
    }
  }
  
  async warmUp(): Promise<void> {
    // Warm up the model with a test embedding
    console.log(`🔥 Warming up Ollama ${this.getModel()}...`);
    await this.generateEmbeddings(['warmup']);
  }
  
  protected async generateEmbeddingsInternal(texts: string[]): Promise<number[][]> {
    const embeddings: number[][] = [];

    // Ollama processes one text at a time for embeddings
    for (const text of texts) {
      const response = await fetch(`${PROVIDER_CONFIG.OLLAMA_BASE_URL}/api/embeddings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: this.getModel(),
          prompt: text
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Ollama error (${response.status}): ${errorText}`);
      }

      const data = await response.json();
      embeddings.push(data.embedding);
    }

    return embeddings;
  }
  
  /**
   * Auto-pull model if not available
   */
  async ensureModelAvailable(): Promise<boolean> {
    const available = await this.isAvailable();
    if (available) return true;

    console.log(`📥 Pulling Ollama model ${this.getModel()}...`);

    try {
      const response = await fetch(`${PROVIDER_CONFIG.OLLAMA_BASE_URL}/api/pull`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: this.getModel(),
          stream: false
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to pull model (${response.status}): ${errorText}`);
      }

      console.log(`✅ Model ${this.getModel()} pulled successfully`);
      return true;
    } catch (error) {
      console.error(`❌ Failed to pull model ${this.getModel()}:`, error);
      return false;
    }
  }
}

console.log('✅ Ollama embedding provider template loaded');