"""
Response Streamer for realtime output delivery.
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncIterator, Callable, Dict, List, Optional

from .models import StreamChunk

logger = logging.getLogger(__name__)


@dataclass
class StreamUpdate:
    """Update to send to client."""
    task_id: str
    content: str
    chunk_index: int
    is_complete: bool = False
    metadata: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class ResponseStreamer:
    """
    Streams model responses to clients in realtime via WebSocket.
    
    Handles buffering, post-processing, and error recovery for
    streaming responses.
    """
    
    def __init__(
        self,
        buffer_size: int = 10,
        flush_interval: float = 0.1,
        enable_post_processing: bool = True
    ):
        """
        Initialize Response Streamer.
        
        Args:
            buffer_size: Number of chunks to buffer before flushing
            flush_interval: Time in seconds between flushes
            enable_post_processing: Enable post-processing of chunks
        """
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self.enable_post_processing = enable_post_processing
        
        # Active streams
        self._active_streams: Dict[str, asyncio.Queue] = {}
        
    async def stream_to_client(
        self,
        task_id: str,
        model_stream: AsyncIterator[StreamChunk],
        send_callback: Callable[[StreamUpdate], None]
    ):
        """
        Stream model output to client via callback.
        
        Args:
            task_id: Unique task identifier
            model_stream: Async iterator of StreamChunk objects
            send_callback: Async callback to send updates to client
        """
        buffer: List[str] = []
        chunk_index = 0
        last_flush = asyncio.get_event_loop().time()
        
        try:
            async for chunk in model_stream:
                # Add to buffer
                if chunk.content:
                    buffer.append(chunk.content)
                
                # Check if we should flush
                current_time = asyncio.get_event_loop().time()
                should_flush = (
                    len(buffer) >= self.buffer_size or
                    (current_time - last_flush) >= self.flush_interval or
                    chunk.finish_reason is not None
                )
                
                if should_flush and buffer:
                    # Combine buffered content
                    content = "".join(buffer)
                    
                    # Apply post-processing if enabled
                    if self.enable_post_processing:
                        content = self._post_process(content)
                    
                    # Send update to client
                    update = StreamUpdate(
                        task_id=task_id,
                        content=content,
                        chunk_index=chunk_index,
                        is_complete=chunk.finish_reason is not None,
                        metadata={
                            "finish_reason": chunk.finish_reason,
                            "model": chunk.model,
                            "provider": chunk.provider.value,
                        }
                    )
                    
                    await send_callback(update)
                    
                    # Clear buffer
                    buffer.clear()
                    chunk_index += 1
                    last_flush = current_time
                
                # Check for completion
                if chunk.finish_reason:
                    break
            
            # Send final update if there's remaining content
            if buffer:
                content = "".join(buffer)
                if self.enable_post_processing:
                    content = self._post_process(content)
                
                update = StreamUpdate(
                    task_id=task_id,
                    content=content,
                    chunk_index=chunk_index,
                    is_complete=True,
                    metadata={"finish_reason": "stop"}
                )
                await send_callback(update)
                
        except asyncio.CancelledError:
            logger.info(f"Stream cancelled for task {task_id}")
            # Send cancellation update
            update = StreamUpdate(
                task_id=task_id,
                content="",
                chunk_index=chunk_index,
                is_complete=True,
                metadata={"finish_reason": "cancelled"}
            )
            await send_callback(update)
            raise
            
        except Exception as e:
            logger.error(f"Error streaming task {task_id}: {e}")
            # Send error update
            update = StreamUpdate(
                task_id=task_id,
                content="",
                chunk_index=chunk_index,
                is_complete=True,
                metadata={
                    "finish_reason": "error",
                    "error": str(e)
                }
            )
            await send_callback(update)
            raise
    
    async def buffer_and_process(
        self,
        stream: AsyncIterator[StreamChunk]
    ) -> str:
        """
        Buffer entire stream and return processed response.
        
        Useful when you need the complete response before processing.
        
        Args:
            stream: Async iterator of StreamChunk objects
            
        Returns:
            Complete processed response
        """
        chunks: List[str] = []
        
        try:
            async for chunk in stream:
                if chunk.content:
                    chunks.append(chunk.content)
                
                if chunk.finish_reason:
                    break
            
            # Combine all chunks
            content = "".join(chunks)
            
            # Apply post-processing
            if self.enable_post_processing:
                content = self._post_process(content)
            
            return content
            
        except Exception as e:
            logger.error(f"Error buffering stream: {e}")
            raise
    
    def _post_process(self, content: str) -> str:
        """
        Apply post-processing to content.
        
        Args:
            content: Raw content from model
            
        Returns:
            Processed content
        """
        # Remove leading/trailing whitespace
        content = content.strip()
        
        # Fix common formatting issues
        content = self._fix_markdown_formatting(content)
        
        # Remove duplicate newlines (more than 2 consecutive)
        while "\n\n\n" in content:
            content = content.replace("\n\n\n", "\n\n")
        
        return content
    
    def _fix_markdown_formatting(self, content: str) -> str:
        """
        Fix common markdown formatting issues.
        
        Args:
            content: Content to fix
            
        Returns:
            Fixed content
        """
        # Ensure code blocks are properly closed
        if content.count("```") % 2 != 0:
            content += "\n```"
        
        # Ensure lists have proper spacing
        lines = content.split("\n")
        fixed_lines = []
        
        for i, line in enumerate(lines):
            fixed_lines.append(line)
            
            # Add blank line before list if needed
            if i > 0 and line.strip().startswith(("-", "*", "1.")) and not lines[i-1].strip().startswith(("-", "*", "1.")):
                if lines[i-1].strip():  # Previous line has content
                    fixed_lines.insert(-1, "")
        
        return "\n".join(fixed_lines)
    
    async def create_stream_queue(self, task_id: str) -> asyncio.Queue:
        """
        Create a queue for streaming updates.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Queue for receiving stream updates
        """
        queue = asyncio.Queue()
        self._active_streams[task_id] = queue
        return queue
    
    async def send_to_queue(self, task_id: str, update: StreamUpdate):
        """
        Send update to task's stream queue.
        
        Args:
            task_id: Task identifier
            update: Stream update to send
        """
        if task_id in self._active_streams:
            await self._active_streams[task_id].put(update)
    
    def close_stream(self, task_id: str):
        """
        Close a stream and clean up resources.
        
        Args:
            task_id: Task identifier
        """
        if task_id in self._active_streams:
            del self._active_streams[task_id]
            logger.debug(f"Closed stream for task {task_id}")
    
    async def handle_stream_interruption(
        self,
        task_id: str,
        error: Exception,
        send_callback: Callable[[StreamUpdate], None]
    ):
        """
        Handle stream interruption gracefully.
        
        Args:
            task_id: Task identifier
            error: Exception that caused interruption
            send_callback: Callback to send error update
        """
        logger.error(f"Stream interrupted for task {task_id}: {error}")
        
        # Send error notification to client
        update = StreamUpdate(
            task_id=task_id,
            content="",
            chunk_index=-1,
            is_complete=True,
            metadata={
                "finish_reason": "error",
                "error": str(error),
                "error_type": type(error).__name__
            }
        )
        
        try:
            await send_callback(update)
        except Exception as e:
            logger.error(f"Failed to send error update: {e}")
        
        # Clean up
        self.close_stream(task_id)
    
    def get_active_streams(self) -> List[str]:
        """
        Get list of active stream task IDs.
        
        Returns:
            List of task IDs with active streams
        """
        return list(self._active_streams.keys())
    
    async def cancel_stream(self, task_id: str):
        """
        Cancel an active stream.
        
        Args:
            task_id: Task identifier
        """
        if task_id in self._active_streams:
            # Send cancellation update
            update = StreamUpdate(
                task_id=task_id,
                content="",
                chunk_index=-1,
                is_complete=True,
                metadata={"finish_reason": "cancelled"}
            )
            
            await self.send_to_queue(task_id, update)
            self.close_stream(task_id)
            
            logger.info(f"Cancelled stream for task {task_id}")


class StreamMultiplexer:
    """
    Multiplexes multiple streams to a single client connection.
    
    Useful for handling multiple concurrent tasks for one user.
    """
    
    def __init__(self):
        """Initialize Stream Multiplexer."""
        self._streams: Dict[str, ResponseStreamer] = {}
    
    def add_stream(self, task_id: str, streamer: ResponseStreamer):
        """Add a stream to multiplex."""
        self._streams[task_id] = streamer
    
    def remove_stream(self, task_id: str):
        """Remove a stream from multiplexing."""
        if task_id in self._streams:
            del self._streams[task_id]
    
    async def multiplex_to_client(
        self,
        send_callback: Callable[[StreamUpdate], None]
    ):
        """
        Multiplex all streams to a single client callback.
        
        Args:
            send_callback: Callback to send updates to client
        """
        # Create tasks for all active streams
        tasks = []
        
        for task_id, streamer in self._streams.items():
            # Each stream sends updates through the same callback
            # The task_id in StreamUpdate distinguishes them
            pass
        
        # Wait for all streams to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
