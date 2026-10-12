"""Split article text into chunks for search: whole paragraphs packed up to a size limit."""

CHUNK_CHARACTERS = 1200


def chunk_text(text: str, *, size: int = CHUNK_CHARACTERS) -> list[str]:
    pieces: list[str] = []
    for paragraph in (" ".join(line.split()) for line in text.splitlines()):
        if not paragraph:
            continue
        while len(paragraph) > size:
            cut = paragraph.rfind(" ", 0, size)
            cut = cut if cut > 0 else size
            pieces.append(paragraph[:cut])
            paragraph = paragraph[cut:].strip()
        pieces.append(paragraph)
    chunks: list[str] = []
    for piece in pieces:
        if chunks and len(chunks[-1]) + 1 + len(piece) <= size:
            chunks[-1] = f"{chunks[-1]}\n{piece}"
        else:
            chunks.append(piece)
    return chunks


def heading_chunk(title: str, lead: str) -> str:
    """Chunk 0 of every document: what we may always show, the title and the publisher's lead."""
    return f"{title}\n{lead}".strip()
