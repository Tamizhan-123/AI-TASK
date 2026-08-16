"""
Two chunking strategies applied to the same 6 articles.

naive_chunk         -- the "current" strategy: fixed-size word-count chunks
                        with overlap, applied blindly to the raw markdown.
                        It has no idea what a markdown table is, so it can
                        (and does) split a table header row from its data
                        rows whenever a chunk boundary happens to fall
                        inside a table.

structure_aware_chunk -- parses markdown structure. Each table (header +
                        separator + every data row) is kept as ONE
                        indivisible chunk. Prose is chunked by
                        section/paragraph. A table row is never split from
                        its header row.

Both return a list of dicts: {"text": str, "section": str|None}. The caller
(indexer/main) attaches the shared article metadata (source_file,
article_id, product_area, last_updated), a chunk_id, and the strategy name.
"""

import re

TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
HEADER_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def naive_chunk(text, chunk_size_words=70, overlap_words=15):
    """
    Fixed-size chunking by word count with overlap. Operates on the raw
    markdown text as a flat sequence of words -- it does not know about
    headers, paragraphs, or tables, so a table's header/separator row can
    end up in one chunk while its data rows end up in the next.
    """
    words = text.split()
    if not words:
        return []

    chunks = []
    step = max(chunk_size_words - overlap_words, 1)
    start = 0
    while start < len(words):
        end = min(start + chunk_size_words, len(words))
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words)
        chunks.append({"text": chunk_text, "section": None})
        if end == len(words):
            break
        start += step

    return chunks


def _flush_paragraph(buffer_lines, section, chunks):
    para = "\n".join(buffer_lines).strip()
    if para:
        chunks.append({"text": para, "section": section})


def structure_aware_chunk(text):
    """
    Markdown-structure-aware chunking.

    - A run of contiguous '|...|' lines (header + separator + data rows) is
      captured as a single chunk, tagged with the section it appeared under.
      This is never split, so a table row can never be separated from its
      header row.
    - Everything else is prose, split into paragraph chunks (blank-line
      separated) tagged with the current section heading.
    """
    lines = text.splitlines()
    chunks = []
    current_section = None
    para_buffer = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        header_match = HEADER_RE.match(line)
        if header_match:
            _flush_paragraph(para_buffer, current_section, chunks)
            para_buffer = []
            current_section = header_match.group(2).strip()
            i += 1
            continue

        if TABLE_ROW_RE.match(line):
            # Flush any prose paragraph in progress before capturing the table.
            _flush_paragraph(para_buffer, current_section, chunks)
            para_buffer = []

            table_lines = []
            while i < n and TABLE_ROW_RE.match(lines[i]):
                table_lines.append(lines[i])
                i += 1
            chunks.append({"text": "\n".join(table_lines), "section": current_section})
            continue

        if line.strip() == "":
            _flush_paragraph(para_buffer, current_section, chunks)
            para_buffer = []
            i += 1
            continue

        para_buffer.append(line)
        i += 1

    _flush_paragraph(para_buffer, current_section, chunks)

    return chunks


if __name__ == "__main__":
    import os

    sample_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "articles",
        "billing-invoice-errors.md",
    )
    with open(sample_path, "r", encoding="utf-8") as fh:
        raw = fh.read()

    body = raw.split("---", 2)[2].strip()

    print("--- naive_chunk ---")
    for idx, c in enumerate(naive_chunk(body)):
        print(f"[{idx}] ({len(c['text'].split())} words) {c['text'][:80]!r}")

    print("\n--- structure_aware_chunk ---")
    for idx, c in enumerate(structure_aware_chunk(body)):
        print(f"[{idx}] section={c['section']!r} {c['text'][:80]!r}")
