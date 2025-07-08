# Agent-MCP/mcp_template/mcp_server_src/db/write_queue.py
import asyncio
import sqlite3
from typing import Any, Callable, Optional, Awaitable
from ..core.config import logger


class DatabaseWriteQueue:
    """
    A queue system for serializing database write operations to prevent SQLite lock contention.

    This class ensures that all write operations (INSERT, UPDATE, DELETE) are executed
    sequentially while allowing concurrent read operations to proceed normally.
    """

    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.worker_task: Optional[asyncio.Task] = None
        self.running: bool = False
        self._stats = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "queue_high_water_mark": 0,
        }

    async def start(self) -> None:
        """Start the write queue worker task."""
        if self.running:
            logger.warning("Database write queue is already running")
            return

        self.running = True
        self.worker_task = asyncio.create_task(self._worker())
        logger.info("Database write queue started")

    async def stop(self) -> None:
        """Stop the write queue worker task and process remaining operations."""
        if not self.running:
            return

        self.running = False

        # Wait for remaining operations to complete
        while not self.queue.empty():
            await asyncio.sleep(0.1)

        # Cancel the worker task
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

        logger.info("Database write queue stopped")

    async def execute_write(self, write_operation: Callable[[], Awaitable[Any]]) -> Any:
        """
        Execute a database write operation through the queue.

        Args:
            write_operation: An async function that performs the database write

        Returns:
            The result of the write operation

        Raises:
            Exception: Any exception raised by the write operation
        """
        if not self.running:
            raise RuntimeError("Database write queue is not running")

        future = asyncio.Future()
        await self.queue.put((write_operation, future))

        # Update queue stats
        current_size = self.queue.qsize()
        if current_size > self._stats["queue_high_water_mark"]:
            self._stats["queue_high_water_mark"] = current_size

        return await future

    async def _worker(self) -> None:
        """Worker task that processes write operations sequentially."""
        logger.info("Database write queue worker started")

        while self.running:
            try:
                # Wait for operation with timeout to allow clean shutdown
                operation, future = await asyncio.wait_for(
                    self.queue.get(), timeout=1.0
                )

                if future.cancelled():
                    continue

                self._stats["total_operations"] += 1

                try:
                    # Execute the write operation
                    result = await operation()
                    future.set_result(result)
                    self._stats["successful_operations"] += 1

                except Exception as e:
                    logger.error(f"Database write operation failed: {e}", exc_info=True)
                    future.set_exception(e)
                    self._stats["failed_operations"] += 1

                # Mark task as done
                self.queue.task_done()

            except asyncio.TimeoutError:
                # Timeout is normal - allows checking if we should continue running
                continue
            except Exception as e:
                logger.error(
                    f"Unexpected error in database write worker: {e}", exc_info=True
                )
                continue

        logger.info("Database write queue worker stopped")

    def get_stats(self) -> dict:
        """Get statistics about the write queue."""
        return {
            **self._stats,
            "current_queue_size": self.queue.qsize(),
            "is_running": self.running,
        }

    def get_queue_size(self) -> int:
        """Get the current queue size."""
        return self.queue.qsize()


# Global write queue instance
_global_write_queue: Optional[DatabaseWriteQueue] = None


def get_write_queue() -> DatabaseWriteQueue:
    """Get the global write queue instance."""
    global _global_write_queue
    if _global_write_queue is None:
        _global_write_queue = DatabaseWriteQueue()
    return _global_write_queue


async def execute_write_operation(operation: Callable[[], Awaitable[Any]]) -> Any:
    """
    Execute a database write operation through the global write queue.

    Args:
        operation: An async function that performs the database write

    Returns:
        The result of the write operation
    """
    queue = get_write_queue()
    return await queue.execute_write(operation)


async def db_write(operation_func: Callable[[], Awaitable[Any]]) -> Any:
    """
    Convenience function to execute database write operations through the queue.

    Args:
        operation_func: An async function that performs the database write

    Returns:
        The result of the write operation
    """
    return await execute_write_operation(operation_func)
