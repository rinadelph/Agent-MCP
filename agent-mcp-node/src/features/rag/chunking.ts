// Simple content chunking system for Agent-MCP Node.js RAG
// Ported from Python features/rag/chunking.py - simple_chunker only

/**
 * Simple text chunking by character count with overlap
 * Basic building block for RAG text processing
 */
export function simpleChunker(
  text: string, 
  chunkSize: number = 500, 
  overlap: number = 50
): string[] {
  if (!text) {
    return [];
  }
  
  if (chunkSize <= 0) {
    throw new Error('chunkSize must be a positive integer');
  }
  
  if (overlap < 0) {
    throw new Error('overlap cannot be negative');
  }
  
  if (overlap >= chunkSize) {
    throw new Error('overlap must be less than chunkSize');
  }

  const chunks: string[] = [];
  let startIndex = 0;
  const textLength = text.length;

  while (startIndex < textLength) {
    const endIndex = startIndex + chunkSize;
    chunks.push(text.substring(startIndex, endIndex));
    
    // Move start_index for the next chunk
    const step = chunkSize - overlap;
    if (step <= 0) {
      // Prevent infinite loop if step is not positive
      break;
    }
    startIndex += step;
  }

  return chunks;
}

console.log('✅ Simple content chunking system loaded');