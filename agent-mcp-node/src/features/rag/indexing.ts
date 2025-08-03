// RAG indexing pipeline for Agent-MCP Node.js
// Ported from Python features/rag/indexing.py with simplified approach

import { createHash } from 'crypto';
import { glob } from 'glob';
import { readFile, stat } from 'fs/promises';
import { join, relative } from 'path';
import { getDbConnection, isVssLoadable } from '../../db/connection.js';
import { generateEmbeddings } from '../../external/openai_service.js';
import { simpleChunker } from './chunking.js';
import { insertChunkWithEmbedding, removeChunksBySource } from './vectorSearch.js';
import { getProjectDir, MCP_DEBUG, DISABLE_AUTO_INDEXING, ADVANCED_EMBEDDINGS } from '../../core/config.js';
import { globalState } from '../../core/globals.js';

/**
 * Directories to ignore during file scanning
 */
const IGNORE_DIRS_FOR_INDEXING = [
  'node_modules',
  '__pycache__',
  'venv',
  'env',
  '.venv',
  '.env',
  'dist',
  'build',
  'site-packages',
  '.git',
  '.idea',
  '.vscode',
  'bin',
  'obj',
  'target',
  '.pytest_cache',
  '.ipynb_checkpoints',
  '.agent'
];

/**
 * File extensions to consider for markdown indexing
 */
const MARKDOWN_EXTENSIONS = ['.md', '.markdown', '.txt'];

/**
 * File extensions to consider for code indexing (advanced mode only)
 */
const CODE_EXTENSIONS = [
  '.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs',
  '.py', '.pyw', '.pyi',
  '.java', '.class',
  '.cs', '.csx',
  '.go', '.rs', '.php', '.rb',
  '.cpp', '.cc', '.cxx', '.c', '.h', '.hpp',
  '.html', '.htm', '.css', '.scss', '.sass', '.less',
  '.json', '.yaml', '.yml', '.xml', '.toml', '.ini'
];

/**
 * Interface for content source to be indexed
 */
interface ContentSource {
  type: 'markdown' | 'code' | 'context' | 'task';
  ref: string;
  content: string;
  modTime: string;
  hash: string;
}

/**
 * Interface for chunk with metadata
 */
interface ChunkWithMetadata {
  text: string;
  metadata: any;
}

/**
 * Get file hash for change detection
 */
function getContentHash(content: string): string {
  return createHash('sha256').update(content, 'utf-8').digest('hex');
}

/**
 * Check if a file path should be ignored
 */
function shouldIgnorePath(filePath: string): boolean {
  const pathParts = filePath.split('/');
  return pathParts.some(part => 
    IGNORE_DIRS_FOR_INDEXING.includes(part) || 
    (part.startsWith('.') && part !== '.' && part !== '..')
  );
}

/**
 * Scan for markdown files in the project directory
 */
async function scanMarkdownFiles(projectDir: string, lastIndexedTime: string): Promise<ContentSource[]> {
  if (DISABLE_AUTO_INDEXING) {
    if (MCP_DEBUG) {
      console.log('📚 Markdown indexing disabled, skipping file scan');
    }
    return [];
  }

  const sources: ContentSource[] = [];
  const patterns = MARKDOWN_EXTENSIONS.map(ext => `**/*${ext}`);
  
  try {
    for (const pattern of patterns) {
      const files = await glob(pattern, { 
        cwd: projectDir,
        absolute: false,
        ignore: IGNORE_DIRS_FOR_INDEXING.map(dir => `**/${dir}/**`)
      });

      for (const file of files) {
        if (shouldIgnorePath(file)) continue;

        try {
          const fullPath = join(projectDir, file);
          const fileStat = await stat(fullPath);
          const modTime = fileStat.mtime.toISOString();
          
          // Skip if not modified since last index
          if (modTime <= lastIndexedTime) continue;

          const content = await readFile(fullPath, 'utf-8');
          const hash = getContentHash(content);
          
          sources.push({
            type: 'markdown',
            ref: file,
            content,
            modTime,
            hash
          });

        } catch (error) {
          console.warn(`Failed to read markdown file ${file}:`, error);
        }
      }
    }

    if (MCP_DEBUG) {
      console.log(`📚 Found ${sources.length} markdown files to consider for indexing`);
    }

  } catch (error) {
    console.error('Error scanning markdown files:', error);
  }

  return sources;
}

/**
 * Scan for code files in the project directory (advanced mode only)
 */
async function scanCodeFiles(projectDir: string, lastIndexedTime: string): Promise<ContentSource[]> {
  if (!ADVANCED_EMBEDDINGS) {
    return [];
  }

  const sources: ContentSource[] = [];
  
  try {
    for (const extension of CODE_EXTENSIONS) {
      const files = await glob(`**/*${extension}`, { 
        cwd: projectDir,
        absolute: false,
        ignore: IGNORE_DIRS_FOR_INDEXING.map(dir => `**/${dir}/**`)
      });

      for (const file of files) {
        if (shouldIgnorePath(file)) continue;

        try {
          const fullPath = join(projectDir, file);
          const fileStat = await stat(fullPath);
          const modTime = fileStat.mtime.toISOString();
          
          // Skip if not modified since last index
          if (modTime <= lastIndexedTime) continue;

          const content = await readFile(fullPath, 'utf-8');
          const hash = getContentHash(content);
          
          sources.push({
            type: 'code',
            ref: file,
            content,
            modTime,
            hash
          });

        } catch (error) {
          console.warn(`Failed to read code file ${file}:`, error);
        }
      }
    }

    if (MCP_DEBUG) {
      console.log(`💻 Found ${sources.length} code files to consider for indexing`);
    }

  } catch (error) {
    console.error('Error scanning code files:', error);
  }

  return sources;
}

/**
 * Scan project context for changes
 */
function scanProjectContext(lastIndexedTime: string): ContentSource[] {
  const db = getDbConnection();
  const sources: ContentSource[] = [];

  try {
    const contextRows = db.prepare(`
      SELECT context_key, value, description, last_updated 
      FROM project_context 
      WHERE last_updated > ?
    `).all(lastIndexedTime);

    for (const row of contextRows) {
      const data = row as any;
      const content = `Context Key: ${data.context_key}\nDescription: ${data.description || ''}\nValue: ${data.value}`;
      const hash = getContentHash(content);

      sources.push({
        type: 'context',
        ref: data.context_key,
        content,
        modTime: data.last_updated,
        hash
      });
    }

    if (MCP_DEBUG) {
      console.log(`🔧 Found ${sources.length} context entries to consider for indexing`);
    }

  } catch (error) {
    console.error('Error scanning project context:', error);
  }

  return sources;
}

/**
 * Scan tasks for changes (advanced mode only)
 */
function scanTasks(lastIndexedTime: string): ContentSource[] {
  if (!ADVANCED_EMBEDDINGS) {
    return [];
  }

  const db = getDbConnection();
  const sources: ContentSource[] = [];

  try {
    const taskRows = db.prepare(`
      SELECT task_id, title, description, status, assigned_to, created_by,
             parent_task, depends_on_tasks, priority, created_at, updated_at
      FROM tasks 
      WHERE updated_at > ?
    `).all(lastIndexedTime);

    for (const row of taskRows) {
      const task = row as any;
      
      // Format task for embedding
      const content = [
        `Task ID: ${task.task_id}`,
        `Title: ${task.title}`,
        `Description: ${task.description || 'No description'}`,
        `Status: ${task.status}`,
        `Priority: ${task.priority}`,
        `Assigned to: ${task.assigned_to || 'Unassigned'}`,
        `Created by: ${task.created_by}`,
        `Parent task: ${task.parent_task || 'None'}`,
        `Dependencies: ${task.depends_on_tasks || 'None'}`,
        `Created: ${task.created_at}`,
        `Updated: ${task.updated_at}`
      ].join('\n');

      const hash = getContentHash(content);

      sources.push({
        type: 'task',
        ref: task.task_id,
        content,
        modTime: task.updated_at,
        hash
      });
    }

    if (MCP_DEBUG) {
      console.log(`📋 Found ${sources.length} tasks to consider for indexing`);
    }

  } catch (error) {
    console.error('Error scanning tasks:', error);
  }

  return sources;
}

/**
 * Get stored hashes and last indexed timestamps from database
 */
function getIndexingMetadata(): { lastIndexed: Record<string, string>; storedHashes: Record<string, string> } {
  const db = getDbConnection();
  
  try {
    const metaRows = db.prepare('SELECT meta_key, meta_value FROM rag_meta').all();
    
    const lastIndexed: Record<string, string> = {};
    const storedHashes: Record<string, string> = {};

    for (const row of metaRows) {
      const data = row as any;
      if (data.meta_key.startsWith('last_indexed_')) {
        lastIndexed[data.meta_key] = data.meta_value;
      } else if (data.meta_key.startsWith('hash_')) {
        storedHashes[data.meta_key] = data.meta_value;
      }
    }

    return { lastIndexed, storedHashes };

  } catch (error) {
    console.error('Error getting indexing metadata:', error);
    return { lastIndexed: {}, storedHashes: {} };
  }
}

/**
 * Update indexing metadata in database
 */
function updateIndexingMetadata(updates: Record<string, string>): void {
  const db = getDbConnection();
  
  try {
    const transaction = db.transaction(() => {
      const upsert = db.prepare(`
        INSERT OR REPLACE INTO rag_meta (meta_key, meta_value)
        VALUES (?, ?)
      `);

      for (const [key, value] of Object.entries(updates)) {
        upsert.run(key, value);
      }
    });

    transaction();

  } catch (error) {
    console.error('Error updating indexing metadata:', error);
  }
}

/**
 * Generate chunks from content based on type
 */
function generateChunks(source: ContentSource): ChunkWithMetadata[] {
  const chunks: ChunkWithMetadata[] = [];
  
  try {
    // For now, use simple chunking for all content types
    // In the future, this can be enhanced with content-specific chunking
    const textChunks = simpleChunker(source.content, 500, 50);
    
    for (const chunk of textChunks) {
      if (chunk && chunk.trim()) {
        chunks.push({
          text: chunk.trim(),
          metadata: {
            source_type: source.type,
            source_ref: source.ref
          }
        });
      }
    }

    if (MCP_DEBUG && chunks.length > 0) {
      console.log(`📄 Generated ${chunks.length} chunks for ${source.type}:${source.ref}`);
    }

  } catch (error) {
    console.error(`Error generating chunks for ${source.type}:${source.ref}:`, error);
  }

  return chunks;
}

/**
 * Process a batch of sources for indexing
 */
async function processSources(sources: ContentSource[]): Promise<void> {
  if (sources.length === 0) {
    return;
  }

  const db = getDbConnection();
  const updatedHashes: Record<string, string> = {};

  try {
    console.log(`🔄 Processing ${sources.length} sources for RAG indexing...`);

    // Generate all chunks first
    const allChunks: Array<{ chunk: ChunkWithMetadata; source: ContentSource }> = [];
    
    for (const source of sources) {
      // Remove existing chunks for this source
      const removedCount = removeChunksBySource(source.ref);
      if (MCP_DEBUG && removedCount > 0) {
        console.log(`🗑️ Removed ${removedCount} existing chunks for ${source.type}:${source.ref}`);
      }

      // Generate new chunks
      const chunks = generateChunks(source);
      for (const chunk of chunks) {
        allChunks.push({ chunk, source });
      }

      // Update hash for this source
      updatedHashes[`hash_${source.type}_${source.ref}`] = source.hash;
    }

    if (allChunks.length === 0) {
      console.log('⚠️ No chunks generated from sources, skipping embedding generation');
      return;
    }

    console.log(`📝 Generated ${allChunks.length} total chunks, generating embeddings...`);

    // Generate embeddings for all chunks
    const chunkTexts = allChunks.map(item => item.chunk.text);
    const embeddings = await generateEmbeddings(chunkTexts);

    // Insert chunks with embeddings
    let successCount = 0;
    for (let i = 0; i < allChunks.length; i++) {
      const item = allChunks[i];
      if (!item) continue;
      
      const { chunk, source } = item;
      const embedding = embeddings[i];

      if (embedding) {
        const chunkId = await insertChunkWithEmbedding(
          chunk.text,
          source.type,
          source.ref,
          chunk.metadata,
          embedding
        );

        if (chunkId) {
          successCount++;
        }
      }
    }

    console.log(`✅ Successfully indexed ${successCount}/${allChunks.length} chunks`);

    // Update metadata timestamps and hashes
    const now = new Date().toISOString();
    const metadataUpdates = {
      ...updatedHashes,
      last_indexed_markdown: now,
      last_indexed_code: now,
      last_indexed_context: now,
      last_indexed_tasks: now
    };

    updateIndexingMetadata(metadataUpdates);

  } catch (error) {
    console.error('Error processing sources for indexing:', error);
  }
}

/**
 * Run a single RAG indexing cycle
 */
export async function runIndexingCycle(): Promise<void> {
  if (!isVssLoadable()) {
    console.warn('⚠️ Vector search not available, skipping RAG indexing cycle');
    return;
  }

  const db = getDbConnection();

  // Check if rag_embeddings table exists
  const tableExists = db.prepare(`
    SELECT name FROM sqlite_master 
    WHERE type='table' AND name='rag_embeddings'
  `).get();

  if (!tableExists) {
    console.warn('⚠️ rag_embeddings table not found, skipping RAG indexing cycle');
    return;
  }

  try {
    if (MCP_DEBUG) {
      console.log('🔄 Starting RAG indexing cycle...');
    }

    const { lastIndexed } = getIndexingMetadata();
    const projectDir = getProjectDir();

    // Default timestamps if not set
    const lastMarkdownTime = lastIndexed.last_indexed_markdown || '1970-01-01T00:00:00Z';
    const lastCodeTime = lastIndexed.last_indexed_code || '1970-01-01T00:00:00Z';
    const lastContextTime = lastIndexed.last_indexed_context || '1970-01-01T00:00:00Z';
    const lastTaskTime = lastIndexed.last_indexed_tasks || '1970-01-01T00:00:00Z';

    // Collect all sources that need processing
    const allSources: ContentSource[] = [
      ...(await scanMarkdownFiles(projectDir, lastMarkdownTime)),
      ...(await scanCodeFiles(projectDir, lastCodeTime)),
      ...scanProjectContext(lastContextTime),
      ...scanTasks(lastTaskTime)
    ];

    // Filter sources that actually need updates based on hash comparison
    const { storedHashes } = getIndexingMetadata();
    const sourcesToProcess = allSources.filter(source => {
      const hashKey = `hash_${source.type}_${source.ref}`;
      const storedHash = storedHashes[hashKey];
      return source.hash !== storedHash;
    });

    if (sourcesToProcess.length === 0) {
      if (MCP_DEBUG) {
        console.log('✅ No new or modified sources found, RAG index is up to date');
      }
      return;
    }

    console.log(`📚 Found ${sourcesToProcess.length} sources needing indexing update`);

    // Process sources in batches to avoid overwhelming the system
    const batchSize = 10;
    for (let i = 0; i < sourcesToProcess.length; i += batchSize) {
      const batch = sourcesToProcess.slice(i, i + batchSize);
      await processSources(batch);
    }

    console.log('✅ RAG indexing cycle completed successfully');

  } catch (error) {
    console.error('❌ Error during RAG indexing cycle:', error);
  }
}

/**
 * Start the periodic RAG indexing process
 */
export function startPeriodicIndexing(intervalSeconds: number = 300): void {
  if (globalState.ragIndexTaskHandle) {
    console.log('⚠️ RAG indexing already running');
    return;
  }

  console.log(`🔄 Starting periodic RAG indexing (every ${intervalSeconds} seconds)`);

  // Initial delay to let server start up
  setTimeout(async () => {
    // Run initial indexing cycle
    await runIndexingCycle();

    // Set up periodic indexing
    globalState.ragIndexTaskHandle = setInterval(async () => {
      if (globalState.serverRunning) {
        await runIndexingCycle();
      }
    }, intervalSeconds * 1000);

  }, 10000); // 10 second initial delay
}

/**
 * Stop the periodic RAG indexing process
 */
export function stopPeriodicIndexing(): void {
  if (globalState.ragIndexTaskHandle) {
    clearInterval(globalState.ragIndexTaskHandle);
    globalState.ragIndexTaskHandle = null;
    console.log('🛑 Stopped periodic RAG indexing');
  }
}

/**
 * Get indexing statistics
 */
export function getIndexingStats(): {
  chunksTotal: number;
  embeddingsTotal: number;
  lastIndexed: Record<string, string>;
  sourceTypes: Record<string, number>;
} {
  const db = getDbConnection();
  
  try {
    // Get total counts
    const chunkResult = db.prepare('SELECT COUNT(*) as count FROM rag_chunks').get() as { count: number };
    const embeddingResult = db.prepare('SELECT COUNT(*) as count FROM rag_embeddings').get() as { count: number };

    // Get source type breakdown
    const sourceTypeResults = db.prepare(`
      SELECT source_type, COUNT(*) as count 
      FROM rag_chunks 
      GROUP BY source_type
    `).all();

    const sourceTypes: Record<string, number> = {};
    for (const row of sourceTypeResults) {
      const data = row as any;
      sourceTypes[data.source_type] = data.count;
    }

    // Get last indexed times
    const { lastIndexed } = getIndexingMetadata();

    return {
      chunksTotal: chunkResult.count,
      embeddingsTotal: embeddingResult.count,
      lastIndexed,
      sourceTypes
    };

  } catch (error) {
    console.error('Error getting indexing stats:', error);
    return {
      chunksTotal: 0,
      embeddingsTotal: 0,
      lastIndexed: {},
      sourceTypes: {}
    };
  }
}

console.log('✅ RAG indexing pipeline loaded');