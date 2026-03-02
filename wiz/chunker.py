"""Split large files into overlapping chunks for LLM context management."""

from dataclasses import dataclass
from .config import CHUNK_SIZE, CHUNK_OVERLAP


@dataclass
class Chunk:
    content: str
    start_line: int
    end_line: int
    chunk_index: int
    total_chunks: int
    filepath: str
    language: str

    @property
    def header(self) -> str:
        return (
            f"File: {self.filepath} ({self.language})\n"
            f"Lines {self.start_line}-{self.end_line} "
            f"(chunk {self.chunk_index + 1}/{self.total_chunks})"
        )


def chunk_file(
    content: str,
    filepath: str,
    language: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[Chunk]:
    """Split file content into overlapping chunks.

    Small files (<=chunk_size lines) return a single chunk.
    Large files are split with overlap to preserve context at boundaries.
    """
    lines = content.splitlines()
    total_lines = len(lines)

    if total_lines <= chunk_size:
        return [Chunk(
            content=content,
            start_line=1,
            end_line=total_lines,
            chunk_index=0,
            total_chunks=1,
            filepath=filepath,
            language=language,
        )]

    chunks = []
    start = 0
    step = chunk_size - overlap

    while start < total_lines:
        end = min(start + chunk_size, total_lines)
        chunk_lines = lines[start:end]
        chunk_content = "\n".join(chunk_lines)

        chunks.append(Chunk(
            content=chunk_content,
            start_line=start + 1,
            end_line=end,
            chunk_index=len(chunks),
            total_chunks=0,  # filled in below
            filepath=filepath,
            language=language,
        ))

        if end >= total_lines:
            break
        start += step

    # Fix total_chunks
    for c in chunks:
        c.total_chunks = len(chunks)

    return chunks


def estimate_tokens(content: str) -> int:
    """Rough token estimate: ~4 chars per token for code."""
    return len(content) // 4
