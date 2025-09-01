// Base Embedding Provider Template
// This is a reference implementation that users can extend for their own providers

import { 
  EmbeddingProvider, 
  EmbeddingProviderError,
  ProviderConfig,
  EmbeddingMetrics,
  ProviderCapabilities
} from '../embeddingProvider.js';
import { EMBEDDING_DIMENSIONS, PROVIDER_CONFIG, MCP_DEBUG } from '../../core/config.js';

/**
 * Base implementation with common functionality for embedding providers
 * Users can extend this class to create their own providers
 */
export abstract class BaseEmbeddingProvider implements EmbeddingProvider {
  protected config: ProviderConfig;
  protected metrics: EmbeddingMetrics[] = [];
  
  constructor(config?: Partial<ProviderConfig>) {
    this.config = {
      type: this.getProviderType(),
      model: this.getDefaultModel(),
      dimensions: EMBEDDING_DIMENSIONS || 1536,
      maxBatchSize: this.getDefaultMaxBatchSize(),
      isLocal: this.isLocalProvider(),
      ...config
    };
  }
  
  /**
   * Get provider type identifier (override in subclass)
   */
  protected abstract getProviderType(): string;
  
  /**
   * Get default model for this provider (override in subclass)
   */
  protected abstract getDefaultModel(): string;
  
  /**
   * Get default max batch size (override in subclass)
   */
  protected abstract getDefaultMaxBatchSize(): number;
  
  /**
   * Whether this is a local provider (override in subclass)
   */
  protected abstract isLocalProvider(): boolean;
  
  /**
   * Check if the provider is available for use (override in subclass)
   */
  abstract isAvailable(): Promise<boolean>;
  
  /**
   * Internal method to generate embeddings (implement in subclass)
   */
  protected abstract generateEmbeddingsInternal(texts: string[]): Promise<number[][]>;
  
  /**
   * Generate embeddings with common error handling and batching
   */
  async generateEmbeddings(texts: string[]): Promise<number[][]> {
    if (texts.length === 0) {
      return [];
    }
    
    const startTime = Date.now();
    let successCount = 0;
    
    try {
      // Check availability first
      if (!await this.isAvailable()) {
        throw new EmbeddingProviderError(
          `${this.getName()} provider is not available`,
          this.getName(),
          'UNKNOWN',
          false
        );
      }
      
      // Process in batches if needed
      const results: number[][] = [];
      const batchSize = this.getMaxBatchSize();
      
      for (let i = 0; i < texts.length; i += batchSize) {
        const batch = texts.slice(i, Math.min(i + batchSize, texts.length));
        
        if (MCP_DEBUG) {
          console.log(`Processing batch ${Math.floor(i / batchSize) + 1}/${Math.ceil(texts.length / batchSize)} (${batch.length} texts)`);
        }
        
        try {
          const batchResults = await this.generateEmbeddingsInternal(batch);
          results.push(...batchResults);
          successCount += batch.length;
        } catch (error) {
          // Handle batch failure
          if (this.shouldRetry(error)) {
            // Retry with exponential backoff
            await this.delay(1000);
            const retryResults = await this.generateEmbeddingsInternal(batch);
            results.push(...retryResults);
            successCount += batch.length;
          } else {
            throw error;
          }
        }
      }
      
      // Normalize dimensions if needed (always output 1536 for simplicity)
      const normalizedResults = this.normalizeDimensions(results);
      
      // Record metrics
      this.recordMetrics(texts.length, Date.now() - startTime, successCount);
      
      return normalizedResults;
      
    } catch (error) {
      // Record failure metrics
      this.recordMetrics(texts.length, Date.now() - startTime, successCount);
      
      // Convert to provider error if needed
      if (error instanceof EmbeddingProviderError) {
        throw error;
      }
      
      throw new EmbeddingProviderError(
        `Failed to generate embeddings: ${error instanceof Error ? error.message : String(error)}`,
        this.getName(),
        this.classifyError(error),
        this.shouldRetry(error)
      );
    }
  }
  
  /**
   * Normalize embeddings to target dimensions (1536)
   */
  protected normalizeDimensions(embeddings: number[][]): number[][] {
    const targetDim = 1536;
    const currentDim = embeddings[0]?.length || 0;
    
    if (currentDim === targetDim || currentDim === 0) {
      return embeddings;
    }
    
    return embeddings.map(embedding => {
      if (currentDim < targetDim) {
        // Pad with zeros
        const padded = [...embedding];
        while (padded.length < targetDim) {
          padded.push(0);
        }
        return padded;
      } else {
        // Truncate
        return embedding.slice(0, targetDim);
      }
    });
  }
  
  /**
   * Classify error type for better handling
   */
  protected classifyError(error: any): 'AUTH' | 'RATE_LIMIT' | 'QUOTA' | 'NETWORK' | 'MODEL' | 'UNKNOWN' {
    const message = error?.message || error?.toString() || '';
    
    if (message.includes('401') || message.includes('auth') || message.includes('unauthorized')) {
      return 'AUTH';
    }
    if (message.includes('429') || message.includes('rate') || message.includes('limit')) {
      return 'RATE_LIMIT';
    }
    if (message.includes('quota') || message.includes('billing')) {
      return 'QUOTA';
    }
    if (message.includes('network') || message.includes('ECONNREFUSED') || message.includes('timeout')) {
      return 'NETWORK';
    }
    if (message.includes('model') || message.includes('not found')) {
      return 'MODEL';
    }
    
    return 'UNKNOWN';
  }
  
  /**
   * Determine if error is retryable
   */
  protected shouldRetry(error: any): boolean {
    const errorType = this.classifyError(error);
    return errorType === 'RATE_LIMIT' || errorType === 'NETWORK';
  }
  
  /**
   * Helper to delay execution
   */
  protected delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
  
  /**
   * Record performance metrics
   */
  protected recordMetrics(textCount: number, durationMs: number, successCount: number) {
    const metric: EmbeddingMetrics = {
      provider: this.getName(),
      model: this.getModel(),
      textCount,
      durationMs,
      avgTimePerText: textCount > 0 ? durationMs / textCount : 0,
      successRate: textCount > 0 ? successCount / textCount : 0,
      timestamp: new Date().toISOString()
    };
    
    this.metrics.push(metric);
    
    // Keep only last 100 metrics
    if (this.metrics.length > 100) {
      this.metrics = this.metrics.slice(-100);
    }
    
    if (MCP_DEBUG) {
      console.log(`📊 ${this.getName()} metrics: ${textCount} texts in ${durationMs}ms (${metric.avgTimePerText.toFixed(1)}ms/text)`);
    }
  }
  
  /**
   * Get recent performance metrics
   */
  getMetrics(): EmbeddingMetrics[] {
    return [...this.metrics];
  }
  
  /**
   * Get average response time from recent metrics
   */
  getAverageResponseTime(): number {
    if (this.metrics.length === 0) return 0;
    
    const totalTime = this.metrics.reduce((sum, m) => sum + m.avgTimePerText, 0);
    return totalTime / this.metrics.length;
  }
  
  getDimensions(): number {
    return this.config.dimensions;
  }
  
  getMaxBatchSize(): number {
    return this.config.maxBatchSize;
  }
  
  getName(): string {
    return this.config.type;
  }
  
  getModel(): string {
    return this.config.model;
  }
  
  getConfig(): ProviderConfig {
    return { ...this.config };
  }
  
  /**
   * Default cost estimation (0 for local providers)
   */
  estimateCost(tokenCount: number): number {
    return this.config.isLocal ? 0 : tokenCount * 0.00001; // Default estimate
  }
  
  /**
   * Get provider capabilities
   */
  getCapabilities(): ProviderCapabilities {
    return {
      supportsBatching: true,
      supportsCustomDimensions: false,
      isLocal: this.config.isLocal,
      hasCosts: !this.config.isLocal,
      supportsModelSelection: true,
      responseTimeCategory: this.config.isLocal ? 'fast' : 'medium',
      qualityCategory: 'good'
    };
  }
}

/**
 * Example custom provider implementation
 * This shows how users can create their own providers
 */
export class ExampleCustomProvider extends BaseEmbeddingProvider {
  protected getProviderType(): string {
    return 'custom';
  }
  
  protected getDefaultModel(): string {
    return 'custom-model-v1';
  }
  
  protected getDefaultMaxBatchSize(): number {
    return 50;
  }
  
  protected isLocalProvider(): boolean {
    return true; // or false for cloud providers
  }
  
  async isAvailable(): Promise<boolean> {
    // Check if your service is available
    try {
      // Example: ping your service endpoint
      const response = await fetch(`${this.config.baseUrl}/health`);
      return response.ok;
    } catch {
      return false;
    }
  }
  
  async warmUp(): Promise<void> {
    // Optional: warm up your model
    console.log('Warming up custom provider...');
    await this.generateEmbeddings(['warmup']);
  }
  
  protected async generateEmbeddingsInternal(texts: string[]): Promise<number[][]> {
    // Implement your embedding generation logic here
    
    // Example for API-based provider:
    /*
    const response = await fetch(`${this.config.baseUrl}/embeddings`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${PROVIDER_CONFIG.PROVIDER_API_KEY}`
      },
      body: JSON.stringify({
        texts,
        model: this.config.model
      })
    });
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    const data = await response.json();
    return data.embeddings;
    */
    
    // Placeholder: return random embeddings for example
    return texts.map(() => {
      const embedding = new Array(768).fill(0).map(() => Math.random() - 0.5);
      return embedding;
    });
  }
}

console.log('✅ Base embedding provider template loaded');