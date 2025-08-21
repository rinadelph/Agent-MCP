// Embedding Provider Factory and Registry
// Central management for all embedding providers with auto-discovery and fallback support

import { EmbeddingProvider, EmbeddingProviderError, ProviderStatus } from './embeddingProvider.js';
import { 
  EMBEDDING_PROVIDER, 
  EMBEDDING_PROVIDERS,
  LOCAL_MODEL_AUTO_DETECT,
  PROVIDER_CONFIG,
  PROVIDER_MODEL_DIMENSIONS,
  MCP_DEBUG 
} from '../core/config.js';

/**
 * Registry of available embedding providers
 * Maps provider type to lazy-loaded provider instance
 */
class EmbeddingProviderRegistry {
  private providers: Map<string, EmbeddingProvider | null> = new Map();
  private providerStatus: Map<string, ProviderStatus> = new Map();
  private initPromises: Map<string, Promise<EmbeddingProvider | null>> = new Map();

  /**
   * Register a provider type (lazy-loaded on first use)
   */
  registerProviderType(type: string) {
    // Provider will be instantiated on first use
    this.providers.set(type, null);
  }

  /**
   * Get or create a provider instance
   */
  async getProvider(type: string): Promise<EmbeddingProvider | null> {
    // Check if we have a cached instance
    const cached = this.providers.get(type);
    if (cached) {
      return cached;
    }

    // Check if already initializing
    const initPromise = this.initPromises.get(type);
    if (initPromise) {
      return initPromise;
    }

    // Start initialization
    const promise = this.initializeProvider(type);
    this.initPromises.set(type, promise);
    
    try {
      const provider = await promise;
      this.providers.set(type, provider);
      this.initPromises.delete(type);
      return provider;
    } catch (error) {
      this.initPromises.delete(type);
      throw error;
    }
  }

  /**
   * Initialize a specific provider type
   */
  private async initializeProvider(type: string): Promise<EmbeddingProvider | null> {
    try {
      console.log(`🔄 Initializing ${type} embedding provider...`);
      
      let provider: EmbeddingProvider | null = null;
      
      switch (type.toLowerCase()) {
        case 'openai':
          // Dynamically import to avoid loading unnecessary providers
          const { OpenAIEmbeddingProvider } = await import('./providers/openai/OpenAIEmbeddingProvider.js');
          provider = new OpenAIEmbeddingProvider();
          break;
          
        case 'ollama':
          const { OllamaEmbeddingProvider } = await import('./providers/ollama/OllamaEmbeddingProvider.js');
          provider = new OllamaEmbeddingProvider();
          break;
          
        case 'gemini':
          const { GeminiEmbeddingProvider } = await import('./providers/gemini/GeminiEmbeddingProvider.js');
          provider = new GeminiEmbeddingProvider();
          break;
          
        case 'huggingface':
          const { HuggingFaceEmbeddingProvider } = await import('./providers/huggingface/HuggingFaceEmbeddingProvider.js');
          provider = new HuggingFaceEmbeddingProvider();
          break;
          
        case 'localserver':
          const { LocalServerEmbeddingProvider } = await import('./providers/localserver/LocalServerEmbeddingProvider.js');
          provider = new LocalServerEmbeddingProvider();
          break;
          
        default:
          console.warn(`⚠️ Unknown provider type: ${type}`);
          return null;
      }
      
      if (provider) {
        // Test provider availability
        const isAvailable = await provider.isAvailable();
        
        // Update status
        const status: ProviderStatus = {
          name: provider.getName(),
          available: isAvailable,
          lastHealthCheck: new Date().toISOString(),
          error: isAvailable ? undefined : 'Provider not available'
        };
        this.providerStatus.set(type, status);
        
        if (isAvailable) {
          console.log(`✅ ${provider.getName()} provider initialized successfully`);
          
          // Warm up the provider if supported
          if (provider.warmUp) {
            console.log(`🔥 Warming up ${provider.getName()} provider...`);
            await provider.warmUp();
          }
          
          return provider;
        } else {
          console.warn(`⚠️ ${provider.getName()} provider is not available`);
          return null;
        }
      }
      
      return null;
    } catch (error) {
      console.error(`❌ Failed to initialize ${type} provider:`, error);
      
      // Update status with error
      const status: ProviderStatus = {
        name: type,
        available: false,
        lastHealthCheck: new Date().toISOString(),
        error: error instanceof Error ? error.message : String(error)
      };
      this.providerStatus.set(type, status);
      
      return null;
    }
  }

  /**
   * Get status for all registered providers
   */
  async getAllProviderStatus(): Promise<ProviderStatus[]> {
    const statuses: ProviderStatus[] = [];
    
    for (const type of this.providers.keys()) {
      const status = this.providerStatus.get(type);
      if (status) {
        statuses.push(status);
      } else {
        // Provider not yet initialized
        statuses.push({
          name: type,
          available: false,
          lastHealthCheck: 'Never',
          error: 'Not initialized'
        });
      }
    }
    
    return statuses;
  }

  /**
   * Clear cached providers (useful for testing or provider switching)
   */
  clearCache() {
    this.providers.clear();
    this.providerStatus.clear();
    this.initPromises.clear();
  }
}

// Global registry instance
const registry = new EmbeddingProviderRegistry();

// Register known provider types
registry.registerProviderType('openai');
registry.registerProviderType('ollama');
registry.registerProviderType('gemini');
registry.registerProviderType('huggingface');
registry.registerProviderType('localserver');

/**
 * Create an embedding provider based on configuration
 */
export async function createProvider(type?: string): Promise<EmbeddingProvider | null> {
  const providerType = type || EMBEDDING_PROVIDER;
  return registry.getProvider(providerType);
}

/**
 * Get the currently configured provider with fallback support
 */
export async function getEmbeddingProvider(): Promise<EmbeddingProvider> {
  // Try providers in order from the fallback chain
  const providerChain = EMBEDDING_PROVIDERS.length > 0 ? EMBEDDING_PROVIDERS : [EMBEDDING_PROVIDER];
  
  for (const providerType of providerChain) {
    try {
      const provider = await createProvider(providerType);
      if (provider && await provider.isAvailable()) {
        if (MCP_DEBUG && providerType !== providerChain[0]) {
          console.log(`🔄 Using fallback provider: ${provider.getName()}`);
        }
        return provider;
      }
    } catch (error) {
      console.warn(`Failed to create ${providerType} provider:`, error);
    }
  }
  
  // If no providers are available, throw an error
  throw new EmbeddingProviderError(
    'No embedding providers available. Please check your configuration.',
    'system',
    'UNKNOWN',
    false
  );
}

/**
 * Get fallback provider when primary fails
 */
export async function getFallbackProvider(excludeProviders: string[] = []): Promise<EmbeddingProvider | null> {
  const providerChain = EMBEDDING_PROVIDERS.length > 0 ? EMBEDDING_PROVIDERS : ['openai', 'ollama', 'gemini', 'huggingface'];
  
  for (const providerType of providerChain) {
    if (excludeProviders.includes(providerType)) {
      continue;
    }
    
    try {
      const provider = await createProvider(providerType);
      if (provider && await provider.isAvailable()) {
        console.log(`🔄 Fallback to ${provider.getName()} provider`);
        return provider;
      }
    } catch (error) {
      if (MCP_DEBUG) {
        console.warn(`Fallback provider ${providerType} not available:`, error);
      }
    }
  }
  
  return null;
}

/**
 * Auto-detect available local embedding services
 */
export async function detectLocalProviders(): Promise<string[]> {
  const availableProviders: string[] = [];
  
  if (!LOCAL_MODEL_AUTO_DETECT) {
    return availableProviders;
  }
  
  console.log('🔍 Auto-detecting local embedding providers...');
  
  // Check Ollama
  try {
    const ollamaUrl = PROVIDER_CONFIG.OLLAMA_BASE_URL;
    const response = await fetch(`${ollamaUrl}/api/tags`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000)
    });
    
    if (response.ok) {
      const data = await response.json();
      if (data.models && data.models.length > 0) {
        console.log(`✅ Ollama detected with ${data.models.length} models`);
        availableProviders.push('ollama');
      }
    }
  } catch (error) {
    if (MCP_DEBUG) {
      console.log('Ollama not detected');
    }
  }
  
  // Check llamafile (common local deployment)
  try {
    const response = await fetch('http://localhost:8080/health', {
      method: 'GET',
      signal: AbortSignal.timeout(5000)
    });
    
    if (response.ok) {
      console.log('✅ Llamafile service detected');
      // Could register a custom llamafile provider
    }
  } catch (error) {
    if (MCP_DEBUG) {
      console.log('Llamafile not detected');
    }
  }
  
  return availableProviders;
}

/**
 * Get all available providers (configured and auto-detected)
 */
export async function getAvailableProviders(): Promise<ProviderStatus[]> {
  // Auto-detect local providers first
  if (LOCAL_MODEL_AUTO_DETECT) {
    await detectLocalProviders();
  }
  
  // Get status for all registered providers
  return registry.getAllProviderStatus();
}

/**
 * Test a specific provider
 */
export async function testProvider(type: string): Promise<boolean> {
  try {
    const provider = await createProvider(type);
    if (!provider) {
      return false;
    }
    
    // Test with a simple embedding
    const testText = 'This is a test embedding';
    const embeddings = await provider.generateEmbeddings([testText]);
    
    if (embeddings.length > 0 && embeddings[0].length === provider.getDimensions()) {
      console.log(`✅ ${provider.getName()} provider test successful`);
      return true;
    }
    
    return false;
  } catch (error) {
    console.error(`❌ ${type} provider test failed:`, error);
    return false;
  }
}

/**
 * Benchmark providers to find the fastest
 */
export async function benchmarkProviders(texts: string[] = []): Promise<Record<string, number>> {
  const benchmarks: Record<string, number> = {};
  
  // Use default test texts if none provided
  if (texts.length === 0) {
    texts = [
      'The quick brown fox jumps over the lazy dog',
      'Machine learning is transforming how we process information',
      'Embedding models convert text into numerical representations'
    ];
  }
  
  const providers = await getAvailableProviders();
  
  for (const status of providers) {
    if (!status.available) continue;
    
    try {
      const provider = await createProvider(status.name);
      if (!provider) continue;
      
      const start = Date.now();
      await provider.generateEmbeddings(texts);
      const duration = Date.now() - start;
      
      benchmarks[status.name] = duration;
      console.log(`⏱️ ${status.name}: ${duration}ms for ${texts.length} texts`);
    } catch (error) {
      console.warn(`Failed to benchmark ${status.name}:`, error);
    }
  }
  
  return benchmarks;
}

/**
 * Clear provider cache (useful when switching providers)
 */
export function clearProviderCache() {
  registry.clearCache();
  console.log('🗑️ Provider cache cleared');
}

// Initialize auto-detection on module load if enabled
if (LOCAL_MODEL_AUTO_DETECT) {
  detectLocalProviders().catch(error => {
    console.warn('Failed to auto-detect local providers:', error);
  });
}

console.log('✅ Embedding provider factory loaded');