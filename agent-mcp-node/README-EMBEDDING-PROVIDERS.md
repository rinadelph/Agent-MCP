# Multi-Provider Embedding System Documentation

## Overview

The Agent-MCP system now supports multiple embedding providers, allowing you to choose between cloud-based services (OpenAI, Gemini) and local models (Ollama, HuggingFace) based on your needs. The system automatically handles provider fallback, dimension normalization, and seamless switching between providers.

## Table of Contents
1. [Quick Start](#quick-start)
2. [Supported Providers](#supported-providers)
3. [Configuration](#configuration)
4. [Provider Implementation Guide](#provider-implementation-guide)
5. [Local Model Setup](#local-model-setup)
6. [Migration Guide](#migration-guide)
7. [Performance Comparison](#performance-comparison)
8. [Troubleshooting](#troubleshooting)

## Quick Start

### 1. Choose Your Provider

Set your preferred embedding provider in your `.env` file:

```bash
# For Local Server (OpenAI-compatible)
EMBEDDING_PROVIDER=localserver
LOCAL_EMBEDDING_URL=http://localhost:4127
LOCAL_EMBEDDING_MODEL=qwen2.5:0.5b

# For OpenAI (default)
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=your_api_key_here

# For Ollama (local)
EMBEDDING_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=nomic-embed-text

# For Gemini
EMBEDDING_PROVIDER=gemini
GEMINI_API_KEY=your_api_key_here

# For HuggingFace
EMBEDDING_PROVIDER=huggingface
HF_TOKEN=your_token_here
```

### 2. Configure Fallback Chain (Optional)

Set up automatic fallback to alternative providers:

```bash
# Primary provider, then fallback options
EMBEDDING_PROVIDERS=ollama,openai,gemini

# Enable auto-detection of local models
LOCAL_MODEL_AUTO_DETECT=true
```

### 3. Test Your Configuration

```bash
# Test the session recovery script includes provider info
node test-session-recovery.js
```

## Supported Providers

### Local Server (OpenAI-Compatible)
- **Models**: qwen2.5:0.5b, any model your server supports
- **Dimensions**: 896 (qwen2.5) - normalized to 1536
- **Type**: Local
- **Cost**: Free
- **Quality**: Good
- **Speed**: Very Fast (14ms per text)
- **Setup**: Run your local embedding server on port 4127

### OpenAI
- **Models**: text-embedding-3-small, text-embedding-3-large, text-embedding-ada-002
- **Dimensions**: 1536 (normalized)
- **Type**: Cloud
- **Cost**: $0.02-$0.13 per 1M tokens
- **Quality**: Excellent
- **Speed**: Medium

### Ollama (Local)
- **Models**: nomic-embed-text, all-minilm, mxbai-embed-large
- **Dimensions**: 384-1024 (normalized to 1536)
- **Type**: Local
- **Cost**: Free
- **Quality**: Good
- **Speed**: Fast (after warm-up)

### Gemini
- **Models**: text-embedding-004
- **Dimensions**: 768 (normalized to 1536)
- **Type**: Cloud
- **Cost**: Free tier available
- **Quality**: Good
- **Speed**: Medium

### HuggingFace
- **Models**: sentence-transformers/all-MiniLM-L6-v2, all-mpnet-base-v2
- **Dimensions**: 384-768 (normalized to 1536)
- **Type**: Cloud/Local
- **Cost**: Free (local) or API pricing
- **Quality**: Good
- **Speed**: Fast (local) or Medium (API)

## Configuration

### Environment Variables

```bash
# Primary Provider Selection
EMBEDDING_PROVIDER=openai|ollama|gemini|huggingface

# Fallback Chain (comma-separated)
EMBEDDING_PROVIDERS=ollama,openai,gemini

# Auto-detect local services
LOCAL_MODEL_AUTO_DETECT=true

# Fixed dimensions for all providers (simplicity)
EMBEDDING_DIMENSIONS=1536

# Provider-specific settings
## OpenAI
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com  # Optional custom endpoint
OPENAI_MODEL=text-embedding-3-large

## Ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=nomic-embed-text

## Gemini
GEMINI_API_KEY=...
GEMINI_MODEL=text-embedding-004

## HuggingFace
HF_TOKEN=hf_...
HF_MODEL=sentence-transformers/all-MiniLM-L6-v2
HF_USE_LOCAL=true  # Use local Transformers.js
```

## Provider Implementation Guide

### Creating a Custom Provider

1. **Extend the Base Provider**:

```typescript
// src/external/providers/custom/CustomProvider.ts
import { BaseEmbeddingProvider } from '../BaseEmbeddingProvider.js';

export class CustomProvider extends BaseEmbeddingProvider {
  protected getProviderType(): string {
    return 'custom';
  }
  
  protected getDefaultModel(): string {
    return 'my-custom-model';
  }
  
  protected getDefaultMaxBatchSize(): number {
    return 50;
  }
  
  protected isLocalProvider(): boolean {
    return true; // or false for cloud
  }
  
  async isAvailable(): Promise<boolean> {
    // Check if your service is available
    try {
      const response = await fetch('http://localhost:8080/health');
      return response.ok;
    } catch {
      return false;
    }
  }
  
  protected async generateEmbeddingsInternal(texts: string[]): Promise<number[][]> {
    // Your embedding generation logic
    const response = await fetch('http://localhost:8080/embeddings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texts })
    });
    
    const data = await response.json();
    return data.embeddings;
  }
}
```

2. **Register Your Provider**:

```typescript
// In embeddingProviderFactory.ts
registry.registerProviderType('custom');

// Add to switch statement
case 'custom':
  const { CustomProvider } = await import('./providers/custom/CustomProvider.js');
  provider = new CustomProvider();
  break;
```

## Local Model Setup

### Ollama Setup

1. **Install Ollama**:
```bash
# macOS/Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Windows
# Download from https://ollama.ai/download
```

2. **Pull Embedding Models**:
```bash
# Recommended models
ollama pull nomic-embed-text     # 768D, balanced
ollama pull mxbai-embed-large    # 1024D, high quality
ollama pull all-minilm            # 384D, fast
```

3. **Verify Installation**:
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Test embedding generation
curl http://localhost:11434/api/embeddings -d '{
  "model": "nomic-embed-text",
  "prompt": "Hello world"
}'
```

### HuggingFace Local Setup

1. **Install Transformers.js**:
```bash
npm install @xenova/transformers
```

2. **Configure for Local Use**:
```bash
HF_USE_LOCAL=true
HF_MODEL=Xenova/all-MiniLM-L6-v2
```

The model will be automatically downloaded on first use.

## Migration Guide

### Switching Providers

1. **Update Configuration**:
```bash
# From OpenAI to Ollama
EMBEDDING_PROVIDER=ollama
OLLAMA_MODEL=nomic-embed-text
```

2. **Re-index if Needed**:
The system automatically handles dimension differences, but for optimal results:
```javascript
// Use the migration tools (when implemented)
await migrateToProvider('ollama');
```

### Handling Dimension Changes

All embeddings are normalized to 1536 dimensions for consistency:
- **Padding**: Smaller embeddings are padded with zeros
- **Truncation**: Larger embeddings are truncated
- **No Re-indexing Required**: The system handles this automatically

## Performance Comparison

### Speed Benchmarks (3 texts, average)

| Provider | First Call | Subsequent | Batch (100) |
|----------|------------|------------|-------------|
| Ollama (local) | 500ms | 50ms | 2s |
| OpenAI | 300ms | 300ms | 3s |
| Gemini | 400ms | 400ms | 4s |
| HuggingFace (local) | 800ms | 100ms | 5s |
| HuggingFace (API) | 500ms | 500ms | 6s |

### Quality Comparison

| Provider | Semantic Accuracy | Multilingual | Context Window |
|----------|------------------|--------------|----------------|
| OpenAI | Excellent | Excellent | 8191 tokens |
| Gemini | Good | Good | 2048 tokens |
| Ollama (nomic) | Good | Fair | 8192 tokens |
| HuggingFace | Good | Varies | 512 tokens |

## Troubleshooting

### Common Issues

#### 1. Provider Not Available
```
⚠️ OpenAI provider is not available
```
**Solution**: Check API key and network connection
```bash
# Verify configuration
echo $OPENAI_API_KEY
```

#### 2. Ollama Connection Failed
```
Ollama not detected
```
**Solution**: Ensure Ollama is running
```bash
# Start Ollama service
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags
```

#### 3. Dimension Mismatch Warnings
```
Model expects 768 dimensions, but EMBEDDING_DIMENSIONS is set to 1536
```
**Solution**: This is handled automatically, but you can set:
```bash
EMBEDDING_DIMENSIONS=1536  # Forces normalization
```

#### 4. Slow First Request
**Solution**: Enable provider warm-up
```javascript
const provider = await createProvider('ollama');
await provider.warmUp();  // Pre-loads model
```

### Debug Mode

Enable detailed logging:
```bash
MCP_DEBUG=true
NODE_ENV=development
```

### Testing Providers

```javascript
// Test all available providers
const results = await benchmarkProviders([
  'Test text 1',
  'Test text 2',
  'Test text 3'
]);

console.log('Provider benchmarks:', results);
// Output: { ollama: 150, openai: 300, gemini: 400 }
```

## Best Practices

### 1. Choose Based on Use Case

- **Development/Testing**: Use Ollama for free, fast local embeddings
- **Production with Budget**: Use OpenAI with fallback to Ollama
- **Privacy-Sensitive**: Use local providers only (Ollama, HuggingFace local)
- **High Volume**: Use Ollama or batch-optimized OpenAI

### 2. Configure Fallbacks

```bash
# Prefer local, fallback to cloud
EMBEDDING_PROVIDERS=ollama,openai,gemini
```

### 3. Monitor Performance

Check provider status regularly:
```bash
curl http://localhost:3002/health
```

### 4. Cache Embeddings

The system includes embedding caching to avoid regenerating identical embeddings.

## Contributing

To add a new provider:

1. Create provider implementation in `src/external/providers/[provider-name]/`
2. Extend `BaseEmbeddingProvider`
3. Register in `embeddingProviderFactory.ts`
4. Add configuration to `config.ts`
5. Update this documentation

## Support

For issues or questions:
- GitHub Issues: https://github.com/rinadelph/Agent-MCP
- Documentation: This file
- Debug logs: Set `MCP_DEBUG=true`