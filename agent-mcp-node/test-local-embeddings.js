#!/usr/bin/env node

// Test script for local embedding server provider
// Tests the embedding server running on port 4127

import dotenv from 'dotenv';
dotenv.config();

const LOCAL_SERVER_URL = process.env.LOCAL_EMBEDDING_URL || 'http://localhost:4127';
const MODEL = process.env.LOCAL_EMBEDDING_MODEL || 'qwen2.5:0.5b';

async function testDirectAPI() {
  console.log('🧪 Testing Direct API Access');
  console.log('='.repeat(50));
  
  try {
    // 1. Check server health/models
    console.log('1️⃣ Checking server availability...');
    const modelsResponse = await fetch(`${LOCAL_SERVER_URL}/v1/models`);
    
    if (modelsResponse.ok) {
      const models = await modelsResponse.json();
      console.log('   ✅ Server is running');
      console.log('   Available models:', models.data?.map(m => m.id).join(', ') || 'No models listed');
    } else {
      console.log('   ❌ Server returned status:', modelsResponse.status);
    }
    
    // 2. Test single embedding
    console.log('\n2️⃣ Testing single text embedding...');
    const singleResponse = await fetch(`${LOCAL_SERVER_URL}/v1/embeddings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        input: "Hello, this is a test embedding",
        model: MODEL
      })
    });
    
    if (singleResponse.ok) {
      const data = await singleResponse.json();
      const embedding = data.data?.[0]?.embedding;
      console.log('   ✅ Single embedding generated');
      console.log(`   Dimensions: ${embedding?.length || 0}`);
      console.log(`   First 5 values: [${embedding?.slice(0, 5).map(v => v.toFixed(4)).join(', ')}...]`);
      console.log(`   Usage tokens: ${data.usage?.total_tokens || 'N/A'}`);
    } else {
      console.log('   ❌ Failed:', await singleResponse.text());
    }
    
    // 3. Test batch embeddings
    console.log('\n3️⃣ Testing batch embeddings...');
    const batchResponse = await fetch(`${LOCAL_SERVER_URL}/v1/embeddings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        input: [
          "First text to embed",
          "Second text with different content",
          "Third text for testing batch processing"
        ],
        model: MODEL
      })
    });
    
    if (batchResponse.ok) {
      const data = await batchResponse.json();
      console.log('   ✅ Batch embeddings generated');
      console.log(`   Count: ${data.data?.length || 0} embeddings`);
      console.log(`   Total tokens: ${data.usage?.total_tokens || 'N/A'}`);
      
      // Verify all embeddings have same dimensions
      const dimensions = data.data?.map(d => d.embedding.length);
      console.log(`   Dimensions: ${dimensions?.join(', ')}`);
      
      // Calculate similarity between first two embeddings
      if (data.data?.length >= 2) {
        const emb1 = data.data[0].embedding;
        const emb2 = data.data[1].embedding;
        const similarity = cosineSimilarity(emb1, emb2);
        console.log(`   Cosine similarity (text 1 & 2): ${similarity.toFixed(4)}`);
      }
    } else {
      console.log('   ❌ Failed:', await batchResponse.text());
    }
    
    // 4. Test performance
    console.log('\n4️⃣ Testing performance...');
    const texts = Array(10).fill(0).map((_, i) => `Test text number ${i + 1}`);
    const startTime = Date.now();
    
    const perfResponse = await fetch(`${LOCAL_SERVER_URL}/v1/embeddings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        input: texts,
        model: MODEL
      })
    });
    
    const duration = Date.now() - startTime;
    
    if (perfResponse.ok) {
      const data = await perfResponse.json();
      console.log(`   ✅ Generated ${texts.length} embeddings in ${duration}ms`);
      console.log(`   Average: ${(duration / texts.length).toFixed(1)}ms per text`);
      console.log(`   Throughput: ${(1000 * texts.length / duration).toFixed(1)} texts/second`);
    } else {
      console.log('   ❌ Performance test failed');
    }
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
  }
}

async function testProviderIntegration() {
  console.log('\n🧪 Testing Provider Integration');
  console.log('='.repeat(50));
  
  try {
    // Dynamically import the provider
    const { LocalServerEmbeddingProvider } = await import('./src/external/providers/localserver/LocalServerEmbeddingProvider.js');
    
    console.log('1️⃣ Creating provider instance...');
    const provider = new LocalServerEmbeddingProvider();
    console.log('   ✅ Provider created');
    console.log(`   Type: ${provider.getName()}`);
    console.log(`   Model: ${provider.getModel()}`);
    console.log(`   Dimensions: ${provider.getDimensions()}`);
    console.log(`   Max batch: ${provider.getMaxBatchSize()}`);
    
    console.log('\n2️⃣ Checking availability...');
    const available = await provider.isAvailable();
    console.log(`   ${available ? '✅' : '❌'} Provider ${available ? 'is' : 'is not'} available`);
    
    if (!available) {
      console.log('   ⚠️ Make sure the embedding server is running on port 4127');
      return;
    }
    
    console.log('\n3️⃣ Warming up provider...');
    await provider.warmUp();
    
    console.log('\n4️⃣ Generating embeddings...');
    const texts = [
      "The quick brown fox jumps over the lazy dog",
      "Machine learning is transforming how we process information",
      "Embeddings convert text into numerical representations"
    ];
    
    const embeddings = await provider.generateEmbeddings(texts);
    console.log(`   ✅ Generated ${embeddings.length} embeddings`);
    console.log(`   Normalized dimensions: ${embeddings[0]?.length || 0} (should be 1536)`);
    
    // Check normalization worked (should be padded to 1536)
    if (embeddings[0]?.length === 1536) {
      console.log('   ✅ Dimension normalization working correctly');
      
      // Check padding (should have zeros at the end)
      const lastValues = embeddings[0].slice(-10);
      const hasPadding = lastValues.every(v => v === 0);
      console.log(`   ${hasPadding ? '✅' : '⚠️'} Padding ${hasPadding ? 'detected' : 'not detected'} at end`);
    }
    
    console.log('\n5️⃣ Testing cost estimation...');
    const cost = provider.estimateCost(1000);
    console.log(`   Cost for 1000 tokens: $${cost.toFixed(6)} (should be 0 for local)`);
    
  } catch (error) {
    console.error('❌ Provider test failed:', error.message);
    console.error(error);
  }
}

// Helper function for cosine similarity
function cosineSimilarity(vec1, vec2) {
  if (vec1.length !== vec2.length) {
    throw new Error('Vectors must have same length');
  }
  
  let dotProduct = 0;
  let norm1 = 0;
  let norm2 = 0;
  
  for (let i = 0; i < vec1.length; i++) {
    dotProduct += vec1[i] * vec2[i];
    norm1 += vec1[i] * vec1[i];
    norm2 += vec2[i] * vec2[i];
  }
  
  return dotProduct / (Math.sqrt(norm1) * Math.sqrt(norm2));
}

// Run tests
async function runAllTests() {
  console.log('🚀 Local Embedding Server Test Suite');
  console.log(`📍 Server URL: ${LOCAL_SERVER_URL}`);
  console.log(`🤖 Model: ${MODEL}`);
  console.log('');
  
  await testDirectAPI();
  await testProviderIntegration();
  
  console.log('\n✅ All tests completed!');
}

runAllTests().catch(console.error);