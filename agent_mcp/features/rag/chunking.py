# Agent-MCP/mcp_template/mcp_server_src/features/rag/chunking.py
import re # For markdown_aware_chunker, though not used in the provided snippet for it.
from typing import List

# No external library imports beyond standard Python for these functions.
# No direct need for logger here unless we add more verbose debugging later.
# If logging is added, import from mcp_server_src.core.config import logger

# Original location: main.py lines 394-401 (simple_chunker function)
def simple_chunker(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Very basic text chunking by character count with overlap.

    Args:
        text: The input string to chunk.
        chunk_size: The desired size of each chunk (in characters).
        overlap: The number of characters to overlap between consecutive chunks.

    Returns:
        A list of text chunks.
    """
    if not text: # Handle empty string input
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer.")
    if overlap < 0:
        raise ValueError("overlap cannot be negative.")
    if overlap >= chunk_size:
        # This would lead to empty or re-processed chunks, or infinite loop if step is 0 or less.
        raise ValueError("overlap must be less than chunk_size.")

    chunks: List[str] = []
    start_index: int = 0
    text_len: int = len(text)

    while start_index < text_len:
        end_index = start_index + chunk_size
        chunks.append(text[start_index:end_index])
        
        # Move start_index for the next chunk
        step = chunk_size - overlap
        if step <= 0: # Should be caught by overlap >= chunk_size, but as a safeguard
            # This prevents an infinite loop if step is not positive.
            # Effectively, if step is not positive, we take one full chunk and stop.
            break
        start_index += step
        
    return chunks

# Original location: main.py lines 403-445 (markdown_aware_chunker function)
def markdown_aware_chunker(
    text: str,
    target_chunk_size: int = 1000, # Original: 1000
    min_chunk_size: int = 200,     # Original: 200
    overlap_lines: int = 2         # Original: 2
) -> List[str]:
    """
    Chunks Markdown text trying to respect structure like headings and paragraphs.
    Aims for `target_chunk_size` but may vary. Chunks smaller than `min_chunk_size`
    are generally avoided unless they are standalone structural elements.

    Args:
        text: The Markdown text to chunk.
        target_chunk_size: The desired approximate size of chunks in characters.
        min_chunk_size: The minimum character size for a chunk before forcing a split
                        on a structural boundary (e.g., new heading/paragraph).
        overlap_lines: The number of trailing lines from a previous chunk to prepend
                       to the current chunk for context.

    Returns:
        A list of Markdown text chunks.
    """
    if not text:
        return []
    if target_chunk_size <= 0 or min_chunk_size <= 0 or overlap_lines < 0:
        raise ValueError("target_chunk_size, min_chunk_size must be positive, and overlap_lines non-negative.")
    if min_chunk_size > target_chunk_size:
        raise ValueError("min_chunk_size cannot be greater than target_chunk_size.")

    chunks: List[str] = []
    current_chunk_lines: List[str] = []
    current_chunk_char_count: int = 0
    
    lines: List[str] = text.split('\n')
    line_buffer_for_overlap: List[str] = []

    for i, line_content in enumerate(lines):
        # Determine if the current line represents a structural break
        is_heading = line_content.strip().startswith('#')
        # A new paragraph is often indicated by an empty line followed by a non-empty line.
        is_new_paragraph = (i > 0 and not lines[i-1].strip() and line_content.strip() != "")

        # Condition to finalize the current chunk and start a new one:
        # 1. If we encounter a heading or a new paragraph,
        # 2. AND the current chunk has reached a reasonable minimum size.
        if (is_heading or is_new_paragraph) and current_chunk_char_count >= min_chunk_size:
            if current_chunk_lines:
                chunks.append("\n".join(current_chunk_lines).strip())
            
            # Start new chunk: Prepend overlap from the buffer.
            current_chunk_lines = line_buffer_for_overlap[:] # Make a copy
            current_chunk_lines.append(line_content)
            current_chunk_char_count = sum(len(l) + 1 for l in current_chunk_lines) -1 # +1 for newline
        else:
            # Add current line to the ongoing chunk
            current_chunk_lines.append(line_content)
            current_chunk_char_count += len(line_content) + 1 # +1 for newline

        # Fallback: If a chunk (even without a structural break) gets excessively large,
        # split it. This prevents extremely long non-breaking segments from creating huge chunks.
        # Original main.py:428 (len(current_chunk) > target_chunk_size * 1.5)
        # The original logic for this fallback was a bit complex and involved `simple_chunker`
        # which is not ideal for a "markdown-aware" chunker.
        # A better fallback here would be to split at the current line if it exceeds a hard limit,
        # or to implement a more sophisticated sentence-level split within this oversized segment.
        # For 1-to-1, the original had a more direct split if current_chunk (as string) got too big.
        # Let's try to replicate the spirit: if current_chunk_char_count gets too large, we split.
        if current_chunk_char_count > target_chunk_size * 1.5 and len(current_chunk_lines) > overlap_lines + 1 : # Ensure we don't split too early if overlap is large
            # Split point: all lines except the last `overlap_lines` (and the current one if it made it too big)
            # This is a simplification of the original complex fallback.
            # The original main.py:428-437 logic was:
            # if len(current_chunk) > target_chunk_size * 1.5:
            #     if current_chunk:
            #         split_point = target_chunk_size
            #         chunks.append(current_chunk[:split_point].strip())
            #         overlap_text = "\n".join(overlap_buffer)
            #         current_chunk = overlap_text + ("\n" if overlap_text else "") + current_chunk[split_point:]
            #     else: current_chunk = line
            # This string-based split is hard to replicate perfectly with line-based processing without
            # re-joining and splitting.
            # Let's simplify: if it's too big, we finalize the current chunk *before* adding the line that made it too big,
            # unless the chunk is just the overlap lines.
            
            # A more direct translation of the original fallback's *intent* (splitting a large string chunk):
            temp_chunk_str = "\n".join(current_chunk_lines)
            if len(temp_chunk_str) > target_chunk_size * 1.5:
                # We need to decide where to split `temp_chunk_str`.
                # The original split at `target_chunk_size` characters.
                # This is tricky because `current_chunk_lines` might not align with that character count.
                # For simplicity and to keep it line-based:
                # If a single line addition makes it too big, the previous chunk is formed.
                # This means the current_chunk_lines *without* the latest line might be one chunk.
                
                # Let's refine the fallback: if adding the current line makes the *string form* too big,
                # then form a chunk from lines *before* the current line (if substantial),
                # then start a new chunk with overlap + current line.
                
                lines_before_current = current_chunk_lines[:-1]
                char_count_before_current = sum(len(l) + 1 for l in lines_before_current) -1
                
                if char_count_before_current >= min_chunk_size: # If what we had *before* this line was substantial
                    chunks.append("\n".join(lines_before_current).strip())
                    current_chunk_lines = line_buffer_for_overlap[:] # Start new with overlap
                    current_chunk_lines.append(line_content) # Add current line to new chunk
                    current_chunk_char_count = sum(len(l) + 1 for l in current_chunk_lines) -1
                # else: the current line is added, and it will be part of a large chunk that might exceed 1.5x target.
                # This part is hard to make 1-to-1 with the original string manipulation fallback while staying line-oriented.
                # The original fallback could split mid-line if not careful.
                # The current line-based approach is generally safer for markdown.
                # The original fallback:
                #   split_point = target_chunk_size
                #   chunks.append(current_chunk[:split_point].strip())
                #   current_chunk = overlap_text + current_chunk[split_point:]
                # This implies character-level splitting, which is different from line-based.
                # For now, the structural split is prioritized. The "too large" fallback is secondary.
                # The current line-based logic will naturally break if lines are very long.

        # Update the overlap buffer (main.py:439-441)
        # This buffer should contain the last `overlap_lines` *actually processed and part of a chunk*.
        # The original `overlap_buffer.append(line)` was inside the loop.
        # It should be lines that *could* form an overlap for the *next* chunk.
        # So, it should be based on `current_chunk_lines`.
        if len(current_chunk_lines) > overlap_lines:
            line_buffer_for_overlap = current_chunk_lines[-overlap_lines:]
        else:
            line_buffer_for_overlap = current_chunk_lines[:]


    # Add the last remaining chunk (main.py:444-445)
    if current_chunk_lines:
        final_chunk_text = "\n".join(current_chunk_lines).strip()
        if final_chunk_text: # Ensure not adding empty strings
             chunks.append(final_chunk_text)

    # Final filter for any empty chunks that might have slipped through (main.py:448)
    return [chunk for chunk in chunks if chunk]