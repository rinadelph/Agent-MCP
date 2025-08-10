# SQLite-Vec Query Syntax Issue Analysis

## Problem Summary

The Agent-MCP system is experiencing sqlite-vec query failures with the error:
```
RAG Query: Database error during vector search: A LIMIT or 'k = ?' constraint is required on vec0 knn queries.
```

## Root Cause Analysis

### Timeline of Events

1. **May 18, 2025** (commit `67d4148d`): Original implementation with correct syntax
2. **May 22, 2025** (commit `494f6454`): Developer confusion led to incorrect `LIMIT ?` syntax
3. **July 4-5, 2025**: Embedding dimension migration recreated the `rag_embeddings` table
4. **July 6, 2025**: Error started appearing due to stricter sqlite-vec requirements

### Key Finding

The code worked for months because the original sqlite-vec table accepted the incorrect syntax. After the July migration recreated the table, the new sqlite-vec configuration enforces stricter syntax requirements.

## Current State Analysis

### Problematic Code Location
**File**: `agent_mcp/features/rag/query.py`
**Lines**: 132-140

```python
sql_vector_search = """
    SELECT c.chunk_text, c.source_type, c.source_ref, c.metadata, r.distance
    FROM rag_embeddings r
    JOIN rag_chunks c ON r.rowid = c.chunk_id
    WHERE r.embedding MATCH ? 
    ORDER BY r.distance
    LIMIT ? 
"""
cursor.execute(sql_vector_search, (query_embedding_json, k_results))
```

### Working Code Pattern
**File**: `agent_mcp/features/rag/query.py`
**Lines**: 354-355

```python
WHERE e.embedding MATCH '[{placeholder_str}]'
  AND k = ?
```

## Code Inconsistency Analysis

### Function 1: `query_rag_system()` - BROKEN
- **Line 136**: `WHERE r.embedding MATCH ?`
- **Line 138**: `LIMIT ?`
- **Status**: ❌ Causes sqlite-vec error

### Function 2: `query_rag_system_with_model()` - WORKING
- **Line 354-355**: `WHERE e.embedding MATCH '[{placeholder_str}]' AND k = ?`
- **Status**: ✅ Works correctly

## Migration Impact

### Recent Database Changes
```bash
# Log entries showing table recreation:
2025-07-04 19:43:22 - WARNING - Embedding dimension has changed. Recreating embeddings table...
2025-07-04 19:49:20 - WARNING - Embedding dimension has changed. Recreating embeddings table...
2025-07-05 12:55:13 - WARNING - Embedding dimension has changed. Recreating embeddings table...
```

### Migration Process
1. `check_embedding_dimension_compatibility()` detected mismatch
2. `handle_embedding_dimension_change()` dropped and recreated table
3. New table created with stricter sqlite-vec requirements
4. Old `LIMIT ?` syntax no longer accepted

## Surgical Fix Required

### Immediate Fix (CRITICAL)
**File**: `agent_mcp/features/rag/query.py`
**Lines**: 132-140

**Change From**:
```python
sql_vector_search = """
    SELECT c.chunk_text, c.source_type, c.source_ref, c.metadata, r.distance
    FROM rag_embeddings r
    JOIN rag_chunks c ON r.rowid = c.chunk_id
    WHERE r.embedding MATCH ? 
    ORDER BY r.distance
    LIMIT ? 
"""
```

**Change To**:
```python
sql_vector_search = """
    SELECT c.chunk_text, c.source_type, c.source_ref, c.metadata, r.distance
    FROM rag_embeddings r
    JOIN rag_chunks c ON r.rowid = c.chunk_id
    WHERE r.embedding MATCH ? AND k = ?
    ORDER BY r.distance
"""
```

### Risk Assessment
- **Risk Level**: LOW
- **Impact**: Fixes RAG query functionality immediately
- **Rollback**: Simple (revert the 2-line change)
- **Testing**: Pattern already proven working in `query_rag_system_with_model()`

## Long-term Robustness Plan

### 1. Query Pattern Standardization
- Create consistent sqlite-vec query patterns across codebase
- Implement query builder pattern for vector searches
- Add version/compatibility detection

### 2. Migration Enhancement
- Add sqlite-vec syntax testing after table recreation
- Store compatible query patterns in database metadata
- Improve migration logging and verification

### 3. Error Handling
- Add specific sqlite-vec error detection
- Implement automatic query pattern fallback
- Enhanced diagnostic logging

### 4. Testing Strategy
- Unit tests for different sqlite-vec query patterns
- Integration tests for migration scenarios
- Version compatibility testing matrix

## Files Requiring Attention

### Immediate (Critical Path)
1. `agent_mcp/features/rag/query.py` - Fix broken query syntax

### Future Robustness
1. `agent_mcp/db/connection.py` - Add sqlite-vec version detection
2. `agent_mcp/db/schema.py` - Enhance migration verification
3. `agent_mcp/features/rag/indexing.py` - Standardize vector operations
4. Create `agent_mcp/db/vector_queries.py` - Centralized query interface

## Verification Steps

### Post-Fix Testing
1. Test RAG query functionality with simple query
2. Verify both vector search functions work identically
3. Check error logs for any remaining sqlite-vec issues
4. Validate migration process doesn't break queries

### Monitoring
1. Monitor sqlite-vec query errors in logs
2. Track RAG query performance and success rates
3. Alert on any future dimension migration issues

## Implementation Priority

### Phase 1: URGENT (Same Day)
- [ ] Apply surgical fix to `query_rag_system()` function
- [ ] Test RAG functionality
- [ ] Verify fix resolves error

### Phase 2: SHORT TERM (1-2 weeks)
- [ ] Standardize query patterns across codebase
- [ ] Add sqlite-vec compatibility detection
- [ ] Enhance migration verification

### Phase 3: LONG TERM (1 month)
- [ ] Implement centralized vector query interface
- [ ] Add comprehensive testing suite
- [ ] Create version compatibility matrix

## Conclusion

This is a classic case where working code broke due to environmental changes (table recreation with stricter requirements). The fix is surgical and low-risk, but the incident highlights the need for better abstraction and version compatibility handling in the sqlite-vec integration.

The immediate priority is applying the proven fix, followed by systematic improvements to prevent similar issues in the future.