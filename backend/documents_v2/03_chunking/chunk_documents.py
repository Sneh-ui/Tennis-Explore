import json
import sys
from pathlib import Path


CURRENT_FILE = Path(__file__).resolve()
DOCUMENTS_V2_DIR = CURRENT_FILE.parent.parent

if str(DOCUMENTS_V2_DIR) not in sys.path:
    sys.path.insert(0, str(DOCUMENTS_V2_DIR))

from config import (
    EXTRACTION_OUTPUT_DIR,
    CHUNK_OUTPUT_DIR,
)


# ---------------------------------------------------------
# CHUNK SETTINGS
# ---------------------------------------------------------

TARGET_WORDS = 180
OVERLAP_WORDS = 40


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def load_json(path):
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def save_json(data, path):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )


def split_text_into_chunks(
    text,
    target_words=TARGET_WORDS,
    overlap_words=OVERLAP_WORDS,
):
    """
    Split text into overlapping word-based chunks.

    Example:
    chunk 1 = words 1-180
    chunk 2 = words 141-320

    This keeps some context between chunks.
    """

    words = text.split()

    if not words:
        return []

    if len(words) <= target_words:
        return [" ".join(words)]

    chunks = []

    start = 0

    while start < len(words):

        end = start + target_words

        chunk_words = words[start:end]

        chunk_text = " ".join(chunk_words)

        chunks.append(chunk_text)

        if end >= len(words):
            break

        start = end - overlap_words

    return chunks


# ---------------------------------------------------------
# PDF CHUNKING
# ---------------------------------------------------------

def chunk_pdf(document):

    chunks = []

    source_file = document["source_file"]

    for page in document.get("pages", []):

        page_number = page["page_number"]

        text = page.get("text", "").strip()

        if not text:
            continue

        page_chunks = split_text_into_chunks(text)

        for index, chunk_text in enumerate(
            page_chunks,
            start=1,
        ):

            chunk_id = (
                f"{Path(source_file).stem}"
                f"_page_{page_number}"
                f"_chunk_{index}"
            )

            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "source_file": source_file,
                    "file_type": "pdf",
                    "page_number": page_number,
                    "slide_number": None,
                    "chunk_index": index,
                    "word_count": len(
                        chunk_text.split()
                    ),
                    "character_count": len(
                        chunk_text
                    ),
                    "text": chunk_text,
                }
            )

    return chunks


# ---------------------------------------------------------
# PPTX CHUNKING
# ---------------------------------------------------------

def chunk_pptx(document):

    chunks = []

    source_file = document["source_file"]

    for slide in document.get("slides", []):

        slide_number = slide["slide_number"]

        text = slide.get("text", "").strip()

        if not text:
            continue

        slide_chunks = split_text_into_chunks(text)

        for index, chunk_text in enumerate(
            slide_chunks,
            start=1,
        ):

            chunk_id = (
                f"{Path(source_file).stem}"
                f"_slide_{slide_number}"
                f"_chunk_{index}"
            )

            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "source_file": source_file,
                    "file_type": "pptx",
                    "page_number": None,
                    "slide_number": slide_number,
                    "chunk_index": index,
                    "word_count": len(
                        chunk_text.split()
                    ),
                    "character_count": len(
                        chunk_text
                    ),
                    "text": chunk_text,
                }
            )

    return chunks


# ---------------------------------------------------------
# PROCESS DOCUMENT
# ---------------------------------------------------------

def process_extracted_document(
    path,
    output_stem=None,
):
    """
    Chunk one extracted document.

    output_stem allows production ingestion to
    preserve a unique resource identity while the
    original source filename remains unchanged.
    """

    document = load_json(path)

    status = document.get(
        "status",
        "unknown",
    )

    if status == "needs_ocr":
        print()
        print(
            f"Skipping OCR-required document: "
            f"{document.get('source_file')}"
        )
        return None

    if status == "failed":
        print()
        print(
            f"Skipping failed document: "
            f"{document.get('source_file')}"
        )
        return None

    file_type = document.get(
        "file_type",
        "",
    ).lower()

    print()
    print(
        f"Chunking: "
        f"{document.get('source_file')}"
    )

    if file_type == "pdf":

        chunks = chunk_pdf(
            document
        )

    elif file_type == "pptx":

        chunks = chunk_pptx(
            document
        )

    else:

        print(
            f"Unsupported type: "
            f"{file_type}"
        )

        return None

    output = {
        "source_file":
            document["source_file"],

        "source_metadata":
            document.get(
                "source_metadata",
                {},
            ),

        "file_type":
            file_type,

        "total_chunks":
            len(chunks),

        "chunk_settings": {
            "target_words":
                TARGET_WORDS,

            "overlap_words":
                OVERLAP_WORDS,
        },

        "chunks":
            chunks,
    }

    # Prefer the production identifier stored by
    # extraction, otherwise preserve old behaviour.
    if output_stem is None:
        output_stem = document.get(
            "output_stem"
        )

    if output_stem is None:
        output_stem = (
            Path(
                document[
                    "source_file"
                ]
            ).stem
        )

    output[
        "output_stem"
    ] = output_stem

    output_name = (
        f"{output_stem}"
        "_chunks.json"
    )

    output_path = (
        CHUNK_OUTPUT_DIR
        / output_name
    )

    save_json(
        output,
        output_path,
    )

    print(
        f"Chunks created: "
        f"{len(chunks)}"
    )

    print(
        f"Saved: {output_path}"
    )

    return output


# ---------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------

def print_summary(results):

    print()
    print("=" * 70)
    print("CHUNKING SUMMARY")
    print("=" * 70)

    total_chunks = 0

    for result in results:

        total_chunks += (
            result["total_chunks"]
        )

        print()
        print(
            f"File   : "
            f"{result['source_file']}"
        )

        print(
            f"Type   : "
            f"{result['file_type'].upper()}"
        )

        print(
            f"Chunks : "
            f"{result['total_chunks']}"
        )

    print()
    print("-" * 70)

    print(
        f"Documents processed : "
        f"{len(results)}"
    )

    print(
        f"Total chunks        : "
        f"{total_chunks}"
    )

    print("-" * 70)


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print()
    print("=" * 70)
    print("TENNIS EXPLORE - V2 CHUNKING")
    print("=" * 70)

    if not EXTRACTION_OUTPUT_DIR.exists():

        print(
            "Extraction output folder not found."
        )

        return

    extracted_files = sorted(
        EXTRACTION_OUTPUT_DIR.glob(
            "*_extracted.json"
        )
    )

    print()
    print(
        f"Extracted files found: "
        f"{len(extracted_files)}"
    )

    if not extracted_files:

        print(
            "No extracted JSON files found."
        )

        return

    results = []

    for path in extracted_files:

        result = (
            process_extracted_document(
                path
            )
        )

        if result:
            results.append(result)

    print_summary(results)


if __name__ == "__main__":
    main()