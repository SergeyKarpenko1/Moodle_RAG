#!/usr/bin/env python3
"""Simple markdown chunker: read .md files and save chunks as .md files."""

import argparse
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Split markdown files into chunks and save as .md.")
    parser.add_argument("--input-dir", default="data/moodle_docs/clean_markdown")
    parser.add_argument("--output-dir", default="data/moodle_docs/chunks_md")
    parser.add_argument("--glob", default="*.md")
    parser.add_argument("--chunk-size", type=int, default=1100)
    parser.add_argument("--chunk-overlap", type=int, default=160)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    files = sorted(input_dir.glob(args.glob))
    total_chunks = 0

    for path in files:
        text = path.read_text(encoding="utf-8")
        chunks = splitter.split_text(text)

        doc_dir = output_dir / path.stem
        doc_dir.mkdir(parents=True, exist_ok=True)

        for i, chunk in enumerate(chunks):
            chunk_path = doc_dir / f"chunk_{i:04d}.md"
            chunk_path.write_text(chunk.strip() + "\n", encoding="utf-8")
            total_chunks += 1

    print(f"Done. Files: {len(files)}, chunks: {total_chunks}")
    print(f"Output dir: {output_dir}")


if __name__ == "__main__":
    main()
