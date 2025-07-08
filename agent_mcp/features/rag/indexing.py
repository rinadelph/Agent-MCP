# Agent-MCP/mcp_template/mcp_server_src/features/rag/indexing.py
import anyio
import time
import datetime
import json
import hashlib
import glob
import os
import sqlite3
from pathlib import Path
from typing import List, Dict, Tuple, Any, Optional, NoReturn

# Attempt to import the OpenAI library
try:
    import openai
except ImportError:
    openai = None

# Imports from our own project modules
from ...core.config import (
    logger,
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSION,
    MAX_EMBEDDING_BATCH_SIZE,
    get_project_dir,
    OPENAI_API_KEY_ENV,  # Also import the API key env variable
    ADVANCED_EMBEDDINGS,  # Import advanced mode flag at module level
)
from ...core import globals as g  # For server_running flag
from ...db.connection import get_db_connection, is_vss_loadable

# We need the actual OpenAI client, not just the service module, for batching logic.
# The client instance is stored in g.openai_client_instance by openai_service.initialize_openai_client()
from ...external.openai_service import (
    get_openai_client,
)  # To get the initialized client

# Import chunking functions from this RAG feature package
from .chunking import simple_chunker, markdown_aware_chunker
from .code_chunking import (
    chunk_code_aware,
    detect_language_family,
    extract_code_entities,
    create_file_summary,
    CODE_EXTENSIONS,
    DOCUMENT_EXTENSIONS,
)

# Original location: main.py lines 512 - 826 (run_rag_indexing_periodically function and its logic)

# Define patterns to ignore for file scanning, as in the original
# Original main.py: 548-552
IGNORE_DIRS_FOR_INDEXING = [
    "node_modules",
    "__pycache__",
    "venv",
    "env",
    ".venv",
    ".env",
    "dist",
    "build",
    "site-packages",
    ".git",
    ".idea",
    ".vscode",
    "bin",
    "obj",
    "target",
    ".pytest_cache",
    ".ipynb_checkpoints",
    ".agent",  # Also ignore the .agent directory itself
]

# Increased concurrency for Tier 3 pricing (5000 RPM)
# Original main.py: 654
MAX_CONCURRENT_EMBEDDING_REQUESTS = 25
# Use smaller batch size for more parallelism
# Original main.py: 660
PARALLEL_EMBEDDING_BATCH_SIZE = 50


async def _get_embeddings_batch_openai(
    batch_chunks: List[str],
    batch_index_start: int,
    results_list: List[Optional[List[float]]],
    openai_api_key: str,  # Pass API key directly for true async client
) -> bool:
    """
    Processes a single batch of embeddings asynchronously using a new AsyncOpenAI client.
    This is a helper for run_rag_indexing_periodically.
    Based on original main.py: lines 656-675.
    """
    # Need to import openai here if not at module level for type hints,
    # or ensure it's available. It's imported at module level with try-except.
    if openai is None:  # Check if openai library was imported successfully
        logger.error("OpenAI library not available for embedding batch.")
        for i in range(len(batch_chunks)):
            if batch_index_start + i < len(results_list):
                results_list[batch_index_start + i] = None  # Mark as failed
        return False

    try:
        # Validate batch_chunks before sending to API
        validated_chunks = []
        for chunk in batch_chunks:
            if isinstance(chunk, str) and chunk.strip():
                validated_chunks.append(chunk)
            else:
                logger.warning(
                    f"Invalid chunk in batch: {type(chunk)} - {repr(chunk)[:50]}"
                )
                validated_chunks.append(
                    " "
                )  # Use single space as fallback to maintain batch size

        # Create a separate async client for each batch for true concurrency
        # Using async client directly with HTTPX to ensure truly parallel requests
        async_client = openai.AsyncOpenAI(api_key=openai_api_key)
        response = await async_client.embeddings.create(
            input=validated_chunks,
            model=EMBEDDING_MODEL,
            dimensions=EMBEDDING_DIMENSION,  # Ensure API returns vector size matching DB schema
        )
        # Store results directly in the provided results list
        for j, item_embedding in enumerate(response.data):
            pos = batch_index_start + j
            if pos < len(results_list):
                results_list[pos] = item_embedding.embedding
        # logger.info(f"Completed embedding batch starting at index {batch_index_start}") # Original: main.py:672
        return True
    except Exception as e:
        logger.error(
            f"OpenAI embedding API error in batch starting at {batch_index_start}: {e}"
        )
        # Mark all embeddings in this batch as failed (None)
        for i in range(len(batch_chunks)):
            if batch_index_start + i < len(results_list):
                results_list[batch_index_start + i] = None
        return False


async def run_rag_indexing_periodically(
    interval_seconds: int = 300, *, task_status=anyio.TASK_STATUS_IGNORED
) -> NoReturn:
    """
    Periodically scans sources (Markdown files, project context) and updates
    the RAG index in the database.
    Original main.py: lines 512 - 826.
    """
    logger.info("Background RAG indexer process starting...")
    # Signal that the task has started successfully for the TaskGroup
    task_status.started()

    await anyio.sleep(10)  # Initial sleep to allow server startup (main.py:515)

    # Get OpenAI client. The service initializes it and stores in g.openai_client_instance
    # The API key itself is also needed for the truly async batch embedding function.
    # This should come from config.OPENAI_API_KEY_ENV
    from ...core.config import OPENAI_API_KEY_ENV as openai_api_key_for_batches

    if not openai_api_key_for_batches:
        logger.error("OpenAI API Key not configured. RAG indexer cannot run.")
        return

    # Check if the OpenAI library itself was loaded
    if openai is None:
        logger.error("OpenAI Python library not loaded. RAG indexer cannot run.")
        return

    while g.server_running:  # Uses global flag (main.py:521)
        cycle_start_time = time.time()

        # Log what content will be indexed based on mode
        if EMBEDDING_DIMENSION == 3072:
            logger.info(
                "Starting RAG index update cycle (advanced mode: markdown, code, context, tasks)..."
            )
        else:
            logger.info(
                "Starting RAG index update cycle (simple mode: markdown, context only)..."
            )

        conn = None  # Initialize conn here for broader scope in try-finally

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Check if VSS is usable (vec0 table exists as a proxy)
            # Original main.py:526-531
            if (
                not is_vss_loadable()
            ):  # This checks the global flag set by initial check
                logger.warning(
                    "Vector Search (sqlite-vec) is not loadable. Skipping RAG indexing cycle."
                )
                await anyio.sleep(interval_seconds * 2)  # Sleep longer if VSS fails
                continue  # Skip to next iteration of the while loop

            # Check for rag_embeddings table specifically
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='rag_embeddings'"
            )
            if cursor.fetchone() is None:
                logger.warning(
                    "Vector table 'rag_embeddings' not found. Skipping RAG indexing cycle. Ensure DB schema is initialized."
                )
                await anyio.sleep(interval_seconds * 2)
                continue

            # Get last indexed timestamps and stored hashes
            # Original main.py:534-535 (last_indexed) and main.py:597-598 (stored_hashes)
            cursor.execute("SELECT meta_key, meta_value FROM rag_meta")
            rag_meta_data = {
                row["meta_key"]: row["meta_value"] for row in cursor.fetchall()
            }
            last_indexed_timestamps = {
                k: v for k, v in rag_meta_data.items() if k.startswith("last_indexed_")
            }
            stored_hashes = {
                k: v for k, v in rag_meta_data.items() if k.startswith("hash_")
            }

            current_project_dir = get_project_dir()  # From config (main.py:537)
            sources_to_check: List[Tuple[str, str, str, Any, str]] = (
                []
            )  # type, ref, content, mod_time/iso, hash

            # 1. Scan Markdown Files and Code Files
            last_md_time_str = last_indexed_timestamps.get(
                "last_indexed_markdown", "1970-01-01T00:00:00Z"
            )
            last_code_time_str = last_indexed_timestamps.get(
                "last_indexed_code", "1970-01-01T00:00:00Z"
            )
            # Ensure timezone awareness for comparison if ISO strings have 'Z' or offset
            last_md_timestamp = datetime.datetime.fromisoformat(
                last_md_time_str.replace("Z", "+00:00")
            ).timestamp()
            last_code_timestamp = datetime.datetime.fromisoformat(
                last_code_time_str.replace("Z", "+00:00")
            ).timestamp()
            max_md_mod_timestamp = last_md_timestamp
            max_code_mod_timestamp = last_code_timestamp

            # Find all markdown files
            all_md_files_found = []
            for md_file_path_str in glob.glob(
                str(current_project_dir / "**/*.md"), recursive=True
            ):
                md_path_obj = Path(md_file_path_str)
                should_ignore = False
                # Path component check from main.py:560-565
                for part in md_path_obj.parts:
                    if part in IGNORE_DIRS_FOR_INDEXING or (
                        part.startswith(".") and part not in [".", ".."]
                    ):
                        should_ignore = True
                        break
                if not should_ignore:
                    all_md_files_found.append(md_path_obj)

            logger.info(
                f"Found {len(all_md_files_found)} markdown files to consider for indexing (after filtering ignored dirs)."
            )

            # Find all code files (only in advanced mode)
            all_code_files_found = []
            if ADVANCED_EMBEDDINGS:
                for extension in CODE_EXTENSIONS:
                    for code_file_path_str in glob.glob(
                        str(current_project_dir / f"**/*{extension}"), recursive=True
                    ):
                        code_path_obj = Path(code_file_path_str)
                        should_ignore = False
                        for part in code_path_obj.parts:
                            if part in IGNORE_DIRS_FOR_INDEXING or (
                                part.startswith(".") and part not in [".", ".."]
                            ):
                                should_ignore = True
                                break
                        if not should_ignore:
                            all_code_files_found.append(code_path_obj)

                logger.info(
                    f"Found {len(all_code_files_found)} code files to consider for indexing (after filtering ignored dirs)."
                )

            # Process markdown files
            for md_path_obj in all_md_files_found:
                try:
                    mod_time = md_path_obj.stat().st_mtime
                    content = md_path_obj.read_text(encoding="utf-8")
                    normalized_path = str(
                        md_path_obj.relative_to(current_project_dir).as_posix()
                    )
                    current_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                    sources_to_check.append(
                        ("markdown", normalized_path, content, mod_time, current_hash)
                    )
                    if mod_time > max_md_mod_timestamp:
                        max_md_mod_timestamp = mod_time
                except Exception as e:
                    logger.warning(
                        f"Failed to read or process markdown file {md_path_obj}: {e}"
                    )

            # Process code files
            for code_path_obj in all_code_files_found:
                try:
                    mod_time = code_path_obj.stat().st_mtime
                    content = code_path_obj.read_text(encoding="utf-8")
                    normalized_path = str(
                        code_path_obj.relative_to(current_project_dir).as_posix()
                    )
                    current_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                    sources_to_check.append(
                        ("code", normalized_path, content, mod_time, current_hash)
                    )
                    if mod_time > max_code_mod_timestamp:
                        max_code_mod_timestamp = mod_time
                except Exception as e:
                    logger.warning(
                        f"Failed to read or process code file {code_path_obj}: {e}"
                    )

            # 2. Scan Project Context (Original main.py:585-603)
            last_ctx_time_str = last_indexed_timestamps.get(
                "last_indexed_context", "1970-01-01T00:00:00Z"
            )
            max_ctx_mod_time_iso = (
                last_ctx_time_str  # Keep as ISO string for direct comparison
            )

            # The original checked `last_updated > ?`. This is good.
            cursor.execute(
                "SELECT context_key, value, description, last_updated FROM project_context WHERE last_updated > ?",
                (last_ctx_time_str,),
            )
            for row in cursor.fetchall():
                key = row["context_key"]
                value_str = row["value"]  # Already a JSON string in DB
                desc = row["description"] or ""
                last_mod_iso = row["last_updated"]
                # Content for hashing and embedding (main.py:593-595)
                content_for_embedding = (
                    f"Context Key: {key}\nDescription: {desc}\nValue: {value_str}"
                )
                current_hash = hashlib.sha256(
                    content_for_embedding.encode("utf-8")
                ).hexdigest()
                sources_to_check.append(
                    ("context", key, content_for_embedding, last_mod_iso, current_hash)
                )
                if last_mod_iso > max_ctx_mod_time_iso:
                    max_ctx_mod_time_iso = last_mod_iso

            # 3. Scan File Metadata (Original main.py:605 - "Skipped for now") - Still skipped.

            # 4. Scan Tasks (only in advanced mode - For System 8)
            max_task_mod_time_iso = last_indexed_timestamps.get(
                "last_indexed_tasks", "1970-01-01T00:00:00Z"
            )

            if ADVANCED_EMBEDDINGS:
                last_task_time_str = last_indexed_timestamps.get(
                    "last_indexed_tasks", "1970-01-01T00:00:00Z"
                )

                # Get tasks that have been updated since last indexing
                cursor.execute(
                    "SELECT task_id, title, description, status, assigned_to, created_by, "
                    "parent_task, depends_on_tasks, priority, created_at, updated_at "
                    "FROM tasks WHERE updated_at > ?",
                    (last_task_time_str,),
                )

                for task_row in cursor.fetchall():
                    task_data = dict(task_row)
                    task_id = task_data["task_id"]
                    last_mod_iso = task_data["updated_at"]

                    # Format task for embedding
                    content_for_embedding = format_task_for_embedding(task_data)
                    current_hash = hashlib.sha256(
                        content_for_embedding.encode("utf-8")
                    ).hexdigest()

                    sources_to_check.append(
                        (
                            "task",
                            task_id,
                            content_for_embedding,
                            last_mod_iso,
                            current_hash,
                        )
                    )

                    if last_mod_iso > max_task_mod_time_iso:
                        max_task_mod_time_iso = last_mod_iso

            # Filter sources based on hash comparison (Original main.py:608-615)
            sources_to_process_for_embedding: List[Tuple[str, str, str, str]] = (
                []
            )  # type, ref, content, current_hash
            for source_type, source_ref, content, _, current_hash in sources_to_check:
                meta_key_for_hash = f"hash_{source_type}_{source_ref}"
                stored_source_hash = stored_hashes.get(meta_key_for_hash)
                if current_hash != stored_source_hash:
                    logger.info(
                        f"Change detected for {source_type}: {source_ref} (Hash mismatch or new). Queued for re-indexing."
                    )
                    sources_to_process_for_embedding.append(
                        (source_type, source_ref, content, current_hash)
                    )
                # else: logger.debug(f"No change for {source_type}:{source_ref} (hash match)")

            if not sources_to_process_for_embedding:
                logger.info(
                    "No new or modified sources found requiring RAG index update."
                )
            else:
                logger.info(
                    f"Processing {len(sources_to_process_for_embedding)} updated/new sources for RAG index."
                )

                processed_hashes_to_update_in_meta: Dict[str, str] = {}

                # Delete existing chunks for sources needing update (Original main.py:619-628)
                logger.info(
                    "Deleting existing chunks and embeddings for sources needing update..."
                )
                delete_count = 0
                for source_type, source_ref, _, _ in sources_to_process_for_embedding:
                    # Delete from embeddings first (using rowid from chunks)
                    # Ensure rag_embeddings table exists before attempting delete
                    cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='rag_embeddings'"
                    )
                    if cursor.fetchone() is not None:
                        res_emb = cursor.execute(
                            "DELETE FROM rag_embeddings WHERE rowid IN (SELECT chunk_id FROM rag_chunks WHERE source_type = ? AND source_ref = ?)",
                            (source_type, source_ref),
                        )
                    # Delete from chunks
                    res_chk = cursor.execute(
                        "DELETE FROM rag_chunks WHERE source_type = ? AND source_ref = ?",
                        (source_type, source_ref),
                    )
                    if res_chk.rowcount > 0:
                        delete_count += res_chk.rowcount
                if delete_count > 0:
                    logger.info(
                        f"Deleted {delete_count} old chunks and their embeddings."
                    )
                    conn.commit()  # Commit deletions

                # Generate chunks and prepare for embedding (Original main.py:631-647)
                all_chunks_texts_to_embed: List[str] = []
                chunk_source_metadata_map: List[
                    Tuple[str, str, str, Dict[str, Any]]
                ] = []  # type, ref, current_hash, metadata for each chunk

                # ADVANCED_EMBEDDINGS is already imported at module level

                for (
                    source_type,
                    source_ref,
                    content,
                    current_hash_of_source,
                ) in sources_to_process_for_embedding:
                    chunks_with_metadata: List[Tuple[str, Dict[str, Any]]] = []

                    if ADVANCED_EMBEDDINGS:
                        # Advanced mode: Use sophisticated chunking
                        if source_type == "markdown":
                            # Markdown-aware chunking
                            text_chunks = markdown_aware_chunker(content)
                            chunks_with_metadata = [
                                (chunk, {"source_type": "markdown"})
                                for chunk in text_chunks
                            ]
                        elif source_type == "code":
                            # Code-aware chunking for code files
                            file_path = current_project_dir / source_ref

                            # First, create a file summary
                            entities = extract_code_entities(content, file_path)
                            file_summary = create_file_summary(
                                content, file_path, entities
                            )
                            summary_text = f"File: {source_ref}\n{json.dumps(file_summary, indent=2)}"
                            chunks_with_metadata.append(
                                (
                                    summary_text,
                                    {"source_type": "code_summary", **file_summary},
                                )
                            )

                            # Then chunk the code
                            code_chunks = chunk_code_aware(content, file_path)
                            chunks_with_metadata.extend(code_chunks)
                        else:
                            # Simple chunking for other types
                            text_chunks = simple_chunker(content)
                            chunks_with_metadata = [
                                (chunk, {"source_type": source_type})
                                for chunk in text_chunks
                            ]
                    else:
                        # Original/Simple mode: Basic chunking for all types
                        text_chunks = simple_chunker(content)
                        # Store minimal metadata
                        chunks_with_metadata = [
                            (chunk, {"source_type": source_type})
                            for chunk in text_chunks
                        ]

                    if not chunks_with_metadata:
                        file_size = len(content) if content else 0
                        logger.warning(
                            f"No chunks generated for {source_type}: {source_ref} (file size: {file_size} bytes, likely empty or only whitespace). Skipping."
                        )
                        continue

                    for chunk_text, metadata in chunks_with_metadata:
                        # Validate chunk before adding - skip empty or whitespace-only chunks
                        if chunk_text and chunk_text.strip():
                            all_chunks_texts_to_embed.append(chunk_text.strip())
                            # Store metadata along with source info
                            chunk_source_metadata_map.append(
                                (
                                    source_type,
                                    source_ref,
                                    current_hash_of_source,
                                    metadata,
                                )
                            )
                        else:
                            logger.warning(
                                f"Skipping empty chunk from {source_type}: {source_ref}"
                            )

                if all_chunks_texts_to_embed:
                    logger.info(
                        f"Generated {len(all_chunks_texts_to_embed)} new chunks for embedding."
                    )

                    all_embeddings_vectors: List[Optional[List[float]]] = [None] * len(
                        all_chunks_texts_to_embed
                    )
                    embeddings_api_successful = (
                        True  # Flag to track overall success of API calls
                    )

                    # Parallel embedding processing (Original main.py:662-690)
                    embedding_api_call_start_time = time.time()
                    # Process batches in groups with controlled concurrency
                    for group_start_idx in range(
                        0,
                        len(all_chunks_texts_to_embed),
                        MAX_CONCURRENT_EMBEDDING_REQUESTS
                        * PARALLEL_EMBEDDING_BATCH_SIZE,
                    ):
                        # Determine how many batches to run in this parallel group
                        num_batches_in_group = 0
                        temp_idx = group_start_idx
                        while (
                            num_batches_in_group < MAX_CONCURRENT_EMBEDDING_REQUESTS
                            and temp_idx < len(all_chunks_texts_to_embed)
                        ):
                            num_batches_in_group += 1
                            temp_idx += PARALLEL_EMBEDDING_BATCH_SIZE

                        logger.info(
                            f"Processing up to {num_batches_in_group} embedding batches in parallel (group starting at chunk {group_start_idx})..."
                        )

                        try:
                            async with anyio.create_task_group() as tg_embed:
                                for i in range(num_batches_in_group):
                                    batch_actual_start_index = (
                                        group_start_idx
                                        + i * PARALLEL_EMBEDDING_BATCH_SIZE
                                    )
                                    if batch_actual_start_index >= len(
                                        all_chunks_texts_to_embed
                                    ):
                                        break  # No more chunks

                                    batch_end_index = min(
                                        batch_actual_start_index
                                        + PARALLEL_EMBEDDING_BATCH_SIZE,
                                        len(all_chunks_texts_to_embed),
                                    )
                                    current_batch_chunks = all_chunks_texts_to_embed[
                                        batch_actual_start_index:batch_end_index
                                    ]

                                    if not current_batch_chunks:
                                        continue

                                    tg_embed.start_soon(
                                        _get_embeddings_batch_openai,
                                        current_batch_chunks,
                                        batch_actual_start_index,
                                        all_embeddings_vectors,
                                        openai_api_key_for_batches,  # Pass the API key
                                    )
                        except (
                            Exception
                        ) as e_tg:  # Catch errors from the task group itself
                            logger.error(
                                f"Error in parallel embedding batch processing task group: {e_tg}"
                            )
                            embeddings_api_successful = (
                                False  # Mark failure if task group fails
                            )

                        if not embeddings_api_successful:
                            break  # Stop if a task group failed

                        # Minimal delay between batch groups (Original main.py:689)
                        if (
                            group_start_idx
                            + MAX_CONCURRENT_EMBEDDING_REQUESTS
                            * PARALLEL_EMBEDDING_BATCH_SIZE
                            < len(all_chunks_texts_to_embed)
                        ):
                            await anyio.sleep(0.1)  # Reduced from 0.2

                    embedding_api_duration = time.time() - embedding_api_call_start_time
                    logger.info(
                        f"Completed all embedding API calls in {embedding_api_duration:.2f} seconds."
                    )

                    # Check for failed embeddings (None values)
                    failed_embedding_count = sum(
                        1 for emb_vec in all_embeddings_vectors if emb_vec is None
                    )
                    if failed_embedding_count > 0:
                        logger.warning(
                            f"{failed_embedding_count} out of {len(all_embeddings_vectors)} embeddings failed to generate."
                        )
                        # If a significant portion failed, mark the overall API call as unsuccessful
                        if (
                            failed_embedding_count > len(all_embeddings_vectors) // 2
                        ):  # More than half failed
                            embeddings_api_successful = False
                            logger.error(
                                "More than half of the embeddings failed. Marking RAG indexing cycle for these sources as unsuccessful."
                            )

                    # Insert new chunks and embeddings into DB (Original main.py:697-722)
                    if embeddings_api_successful:
                        logger.info(
                            "Inserting new chunks and embeddings into the database..."
                        )
                        inserted_count = 0
                        indexed_at_iso = datetime.datetime.now().isoformat()
                        for i, chunk_text_to_insert in enumerate(
                            all_chunks_texts_to_embed
                        ):
                            embedding_vector = all_embeddings_vectors[i]
                            if embedding_vector is None:
                                logger.warning(
                                    f"Skipping chunk {i} for DB insertion due to missing embedding."
                                )
                                continue

                            (
                                source_type,
                                source_ref,
                                current_hash_of_source,
                                chunk_metadata,
                            ) = chunk_source_metadata_map[i]
                            try:
                                # Store chunk with optional metadata
                                metadata_json = (
                                    json.dumps(chunk_metadata)
                                    if chunk_metadata
                                    else None
                                )
                                cursor.execute(
                                    "INSERT INTO rag_chunks (source_type, source_ref, chunk_text, indexed_at, metadata) VALUES (?, ?, ?, ?, ?)",
                                    (
                                        source_type,
                                        source_ref,
                                        chunk_text_to_insert,
                                        indexed_at_iso,
                                        metadata_json,
                                    ),
                                )
                                chunk_rowid = cursor.lastrowid  # This is the chunk_id

                                embedding_json_str = json.dumps(embedding_vector)
                                cursor.execute(
                                    "INSERT INTO rag_embeddings (rowid, embedding) VALUES (?, ?)",
                                    (chunk_rowid, embedding_json_str),
                                )
                                inserted_count += 1
                                # Mark this source's hash to be updated in rag_meta
                                meta_key_for_hash_update = (
                                    f"hash_{source_type}_{source_ref}"
                                )
                                processed_hashes_to_update_in_meta[
                                    meta_key_for_hash_update
                                ] = current_hash_of_source
                            except sqlite3.Error as db_err:
                                logger.error(
                                    f"DB Error inserting chunk/embedding for {source_type}:{source_ref} (Chunk index {i}): {db_err}"
                                )
                                # If one insert fails, we might lose its hash update.
                                # Consider if transaction should be per source or all-or-nothing for the cycle.
                                # Original code continued, so we do too.
                            except Exception as e_ins:
                                logger.error(
                                    f"Unexpected error inserting chunk/embedding: {e_ins}",
                                    exc_info=True,
                                )

                        logger.info(
                            f"Successfully inserted {inserted_count} new chunks/embeddings."
                        )

                        # Update rag_meta with the new hashes for successfully processed sources
                        # Original main.py:725-728
                        if processed_hashes_to_update_in_meta:
                            logger.info(
                                f"Updating {len(processed_hashes_to_update_in_meta)} source hashes in rag_meta..."
                            )
                            meta_update_tuples = list(
                                processed_hashes_to_update_in_meta.items()
                            )
                            cursor.executemany(
                                "INSERT OR REPLACE INTO rag_meta (meta_key, meta_value) VALUES (?, ?)",
                                meta_update_tuples,
                            )
                    else:
                        logger.warning(
                            "Skipping DB insertion and hash updates for this RAG cycle due to embedding API errors."
                        )

            # Update last indexed *timestamps* in rag_meta (Original main.py:731-737)
            # Only update if the embedding part (if attempted) was successful or no embeddings were needed.
            # The 'embeddings_api_successful' flag covers this.
            if (
                "embeddings_api_successful" not in locals() or embeddings_api_successful
            ):  # Check if flag exists and is True
                new_md_time_iso = (
                    datetime.datetime.fromtimestamp(max_md_mod_timestamp).isoformat()
                    + "Z"
                )
                cursor.execute(
                    "INSERT OR REPLACE INTO rag_meta (meta_key, meta_value) VALUES (?, ?)",
                    ("last_indexed_markdown", new_md_time_iso),
                )
                cursor.execute(
                    "INSERT OR REPLACE INTO rag_meta (meta_key, meta_value) VALUES (?, ?)",
                    ("last_indexed_context", max_ctx_mod_time_iso),
                )

                # Only update code and tasks timestamps in advanced mode
                if ADVANCED_EMBEDDINGS:
                    new_code_time_iso = (
                        datetime.datetime.fromtimestamp(
                            max_code_mod_timestamp
                        ).isoformat()
                        + "Z"
                    )
                    cursor.execute(
                        "INSERT OR REPLACE INTO rag_meta (meta_key, meta_value) VALUES (?, ?)",
                        ("last_indexed_code", new_code_time_iso),
                    )
                    cursor.execute(
                        "INSERT OR REPLACE INTO rag_meta (meta_key, meta_value) VALUES (?, ?)",
                        ("last_indexed_tasks", max_task_mod_time_iso),
                    )
                # Add other source types here
            else:
                logger.warning(
                    "Skipping rag_meta timestamp updates due to errors in the embedding/indexing cycle."
                )

            conn.commit()  # Commit all DB changes for this cycle

            # Diagnostic query (Original main.py:740-747)
            try:
                diag_cursor = conn.cursor()  # Use a new cursor or the same one
                diag_cursor.execute("SELECT COUNT(*) FROM rag_chunks")
                chunk_count_diag = diag_cursor.fetchone()[0]
                diag_cursor.execute("SELECT COUNT(*) FROM rag_embeddings")
                embedding_count_diag = diag_cursor.fetchone()[0]
                logger.info(
                    f"DB RAG DIAGNOSTIC: Found {chunk_count_diag} chunks and {embedding_count_diag} embeddings post-cycle."
                )
            except Exception as e_diag:
                logger.error(f"Error running RAG database diagnostics: {e_diag}")

        except sqlite3.OperationalError as e_sqlite_op:  # main.py:750-753
            if (
                "no such module: vec0" in str(e_sqlite_op)
                or "vector search requires" in str(e_sqlite_op).lower()
            ):
                logger.warning(
                    f"Vector search module (vec0) not available or table missing. RAG indexing cycle skipped. Error: {e_sqlite_op}"
                )
                g.global_vss_load_successful = (
                    False  # Mark VSS as not usable if this happens
                )
            else:
                logger.error(
                    f"Database operational error in RAG indexing cycle: {e_sqlite_op}",
                    exc_info=True,
                )
        except Exception as e_cycle:  # main.py:756 (general catch-all for the cycle)
            logger.error(f"Error in RAG indexing cycle: {e_cycle}", exc_info=True)
        finally:
            if conn:
                conn.close()

        elapsed_cycle_time = time.time() - cycle_start_time
        logger.info(
            f"RAG index update cycle finished in {elapsed_cycle_time:.2f} seconds."
        )

        # Sleep interval (Original main.py:760)
        # Adjusted sleep: min 60s, or interval_seconds, whichever is larger.
        # The original had `max(30, interval_seconds / 5)` which could be very short.
        # Let's use a more stable sleep or make it configurable.
        # For 1-to-1, let's use the original logic:
        sleep_duration = max(30, interval_seconds // 5)
        logger.debug(f"RAG indexer sleeping for {sleep_duration} seconds.")
        await anyio.sleep(sleep_duration)

    logger.info("Background RAG indexer process stopped.")


# This function, run_rag_indexing_periodically, will be started as a background task
# by the server lifecycle management (e.g., in app/server_lifecycle.py).


# Task indexing functions for System 8
async def index_task_data(task_id: str, task_data: Dict[str, Any]) -> None:
    """
    Index a single task into the RAG system.

    Args:
        task_id: Task ID to index
        task_data: Complete task data dictionary
    """
    if not is_vss_loadable():
        logger.warning("Cannot index task - VSS not available")
        return

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Format task for embedding
        content = format_task_for_embedding(task_data)

        # Generate chunks (tasks are usually small, so one chunk is fine)
        chunks = simple_chunker(content, chunk_size=2000)

        # Delete existing chunks for this task
        cursor.execute(
            "DELETE FROM rag_embeddings WHERE rowid IN "
            "(SELECT chunk_id FROM rag_chunks WHERE source_type = ? AND source_ref = ?)",
            ("task", task_id),
        )
        cursor.execute(
            "DELETE FROM rag_chunks WHERE source_type = ? AND source_ref = ?",
            ("task", task_id),
        )

        # Get OpenAI client for embeddings
        client = get_openai_client()
        if not client:
            logger.error("OpenAI client not available for task indexing")
            return

        # Generate embeddings for each chunk
        for chunk_text in chunks:
            try:
                # Generate embedding
                embedding_response = client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=chunk_text,
                    dimensions=EMBEDDING_DIMENSION,
                )
                embedding_vector = embedding_response.data[0].embedding

                # Insert chunk
                cursor.execute(
                    "INSERT INTO rag_chunks (source_type, source_ref, chunk_text, indexed_at) "
                    "VALUES (?, ?, ?, ?)",
                    ("task", task_id, chunk_text, datetime.datetime.now().isoformat()),
                )
                chunk_id = cursor.lastrowid

                # Insert embedding
                cursor.execute(
                    "INSERT INTO rag_embeddings (rowid, embedding) VALUES (?, ?)",
                    (chunk_id, embedding_vector),
                )

            except Exception as e:
                logger.error(f"Error generating embedding for task {task_id}: {e}")

        conn.commit()
        logger.info(f"Successfully indexed task {task_id}")

    except Exception as e:
        logger.error(f"Error indexing task {task_id}: {e}", exc_info=True)
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


async def index_all_tasks() -> None:
    """Index all tasks from the database."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get all tasks
        cursor.execute(
            "SELECT task_id, title, description, status, assigned_to, created_by, "
            "parent_task, depends_on_tasks, priority, created_at, updated_at "
            "FROM tasks"
        )

        tasks = cursor.fetchall()
        logger.info(f"Indexing {len(tasks)} tasks for RAG")

        for task_row in tasks:
            task_data = dict(task_row)
            # Parse JSON fields
            if task_data.get("depends_on_tasks"):
                try:
                    task_data["depends_on_tasks"] = json.loads(
                        task_data["depends_on_tasks"]
                    )
                except json.JSONDecodeError:
                    task_data["depends_on_tasks"] = []

            await index_task_data(task_data["task_id"], task_data)

        # Update last indexed time
        cursor.execute(
            "INSERT OR REPLACE INTO rag_meta (meta_key, meta_value) VALUES (?, ?)",
            ("last_indexed_tasks", datetime.datetime.now().isoformat()),
        )
        conn.commit()

    except Exception as e:
        logger.error(f"Error indexing all tasks: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()


def format_task_for_embedding(task_data: Dict[str, Any]) -> str:
    """
    Format task data into text suitable for embedding.

    Args:
        task_data: Task data dictionary

    Returns:
        Formatted text for embedding
    """
    parts = [
        f"Task ID: {task_data.get('task_id', 'unknown')}",
        f"Title: {task_data.get('title', 'Untitled')}",
        f"Description: {task_data.get('description', 'No description')}",
        f"Status: {task_data.get('status', 'unknown')}",
        f"Priority: {task_data.get('priority', 'medium')}",
        f"Assigned to: {task_data.get('assigned_to', 'unassigned')}",
        f"Created by: {task_data.get('created_by', 'unknown')}",
    ]

    if task_data.get("parent_task"):
        parts.append(f"Parent task: {task_data['parent_task']}")
    else:
        parts.append("Parent task: None (root level)")

    depends_on = task_data.get("depends_on_tasks", [])
    if isinstance(depends_on, str):
        try:
            depends_on = json.loads(depends_on)
        except:
            depends_on = []

    if depends_on:
        parts.append(f"Dependencies: {', '.join(depends_on)}")
    else:
        parts.append("Dependencies: None")

    # Add metadata
    parts.extend(
        [
            f"Created at: {task_data.get('created_at', 'unknown')}",
            f"Updated at: {task_data.get('updated_at', 'unknown')}",
        ]
    )

    return "\n".join(parts)
