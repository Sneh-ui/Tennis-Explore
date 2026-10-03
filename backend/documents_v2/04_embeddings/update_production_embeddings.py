import json
import os
import sys
from pathlib import Path

import numpy as np
import psycopg
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer


# ---------------------------------------------------------
# PROJECT CONFIG
# ---------------------------------------------------------

CURRENT_FILE = Path(__file__).resolve()
DOCUMENTS_V2_DIR = CURRENT_FILE.parent.parent

if str(DOCUMENTS_V2_DIR) not in sys.path:
    sys.path.insert(0, str(DOCUMENTS_V2_DIR))

from config import (
    EMBEDDING_OUTPUT_DIR,
    EMBEDDING_MODEL_NAME,
)


load_dotenv()


# ---------------------------------------------------------
# OUTPUT FILES
# ---------------------------------------------------------

EMBEDDINGS_PATH = (
    EMBEDDING_OUTPUT_DIR
    / "production_chunk_embeddings.npy"
)

METADATA_PATH = (
    EMBEDDING_OUTPUT_DIR
    / "production_chunk_metadata.json"
)


# ---------------------------------------------------------
# DATABASE CONFIG
# ---------------------------------------------------------

def get_db_config():
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "dbname": os.getenv(
            "DB_NAME",
            "tennis_rankings",
        ),
        "user": os.getenv(
            "DB_USER",
            os.getenv("USER", ""),
        ),
        "password": (
            os.getenv("DB_PASSWORD") or None
        ),
    }


# ---------------------------------------------------------
# LOAD EXISTING RETRIEVAL ARTIFACTS
# ---------------------------------------------------------

def load_existing_artifacts():

    if not EMBEDDINGS_PATH.exists():
        raise FileNotFoundError(
            "Production embeddings were not found: "
            f"{EMBEDDINGS_PATH}"
        )

    if not METADATA_PATH.exists():
        raise FileNotFoundError(
            "Production metadata was not found: "
            f"{METADATA_PATH}"
        )

    embeddings = np.load(
        EMBEDDINGS_PATH
    ).astype("float32")

    with METADATA_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        metadata = json.load(file)

    if len(metadata) != len(embeddings):
        raise ValueError(
            "Existing metadata and embedding counts "
            "do not match."
        )

    return metadata, embeddings


# ---------------------------------------------------------
# LOAD DATABASE CHUNK IDS
# ---------------------------------------------------------

def load_database_chunk_ids():

    query = """
        SELECT c.chunk_db_id
        FROM unstructured.document_chunks AS c
        WHERE c.chunk_text IS NOT NULL
          AND BTRIM(c.chunk_text) <> ''
        ORDER BY c.chunk_db_id
    """

    config = get_db_config()

    with psycopg.connect(**config) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

    return [
        row[0]
        for row in rows
    ]


# ---------------------------------------------------------
# LOAD NEW CHUNKS
# ---------------------------------------------------------

def load_new_chunks(new_chunk_ids):

    if not new_chunk_ids:
        return []

    query = """
        SELECT
            c.chunk_db_id,
            c.source_chunk_id,
            d.file_name,
            d.file_type,
            c.page_number,
            c.slide_number,
            c.word_count,
            c.chunk_text
        FROM unstructured.document_chunks AS c
        JOIN unstructured.documents AS d
            ON d.document_id = c.document_id
        WHERE c.chunk_db_id = ANY(%s)
          AND c.chunk_text IS NOT NULL
          AND BTRIM(c.chunk_text) <> ''
        ORDER BY c.chunk_db_id
    """

    config = get_db_config()

    with psycopg.connect(**config) as conn:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (new_chunk_ids,),
            )
            rows = cur.fetchall()

    chunks = []

    for row in rows:
        chunks.append(
            {
                "chunk_db_id": row[0],
                "chunk_id": row[1],
                "source_file": row[2],
                "file_type": row[3],
                "page_number": row[4],
                "slide_number": row[5],
                "word_count": row[6],
                "text": row[7],
            }
        )

    return chunks


# ---------------------------------------------------------
# VALIDATION
# ---------------------------------------------------------

def validate_existing_metadata(metadata):

    chunk_db_ids = [
        item["chunk_db_id"]
        for item in metadata
    ]

    if len(chunk_db_ids) != len(
        set(chunk_db_ids)
    ):
        raise ValueError(
            "Duplicate chunk_db_id values exist "
            "in production metadata."
        )

    for expected_vector_id, item in enumerate(
        metadata
    ):
        if item["vector_id"] != expected_vector_id:
            raise ValueError(
                "Existing vector_id alignment "
                "is invalid."
            )


def validate_updated_artifacts(
    metadata,
    embeddings,
    database_chunk_ids=None,
):

    if len(metadata) != len(embeddings):
        raise ValueError(
            "Updated metadata and embedding "
            "counts do not match."
        )

    chunk_db_ids = [
        item["chunk_db_id"]
        for item in metadata
    ]

    if len(chunk_db_ids) != len(
        set(chunk_db_ids)
    ):
        raise ValueError(
            "Duplicate chunk_db_id detected "
            "after update."
        )

    for expected_vector_id, item in enumerate(
        metadata
    ):
        if item["vector_id"] != expected_vector_id:
            raise ValueError(
                "Updated vector_id alignment "
                "is invalid."
            )

    if database_chunk_ids is not None:

        artifact_ids = set(chunk_db_ids)
        database_ids = set(database_chunk_ids)

        if artifact_ids != database_ids:
            missing = database_ids - artifact_ids
            stale = artifact_ids - database_ids

            raise ValueError(
                "Retrieval artifacts do not exactly "
                "match PostgreSQL. "
                f"Missing IDs: {len(missing)}, "
                f"Stale IDs: {len(stale)}"
            )


# ---------------------------------------------------------
# REMOVE STALE ARTIFACTS
# ---------------------------------------------------------

def remove_stale_artifacts(
    metadata,
    embeddings,
    database_chunk_id_set,
):

    keep_indices = [
        index
        for index, item in enumerate(metadata)
        if item["chunk_db_id"]
        in database_chunk_id_set
    ]

    filtered_metadata = [
        metadata[index]
        for index in keep_indices
    ]

    filtered_embeddings = embeddings[
        keep_indices
    ].astype("float32")

    for vector_id, item in enumerate(
        filtered_metadata
    ):
        item["vector_id"] = vector_id

    return (
        filtered_metadata,
        filtered_embeddings,
    )


# ---------------------------------------------------------
# SAFE SAVE
# ---------------------------------------------------------

def save_updated_artifacts(
    metadata,
    embeddings,
    database_chunk_ids,
):

    temp_embeddings_path = (
        EMBEDDING_OUTPUT_DIR
        / "production_chunk_embeddings.tmp.npy"
    )

    temp_metadata_path = (
        EMBEDDING_OUTPUT_DIR
        / "production_chunk_metadata.tmp.json"
    )

    np.save(
        temp_embeddings_path,
        embeddings,
    )

    with temp_metadata_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metadata,
            file,
            ensure_ascii=False,
            indent=2,
        )

    # Read temporary files back before replacing
    # the working production artifacts.

    test_embeddings = np.load(
        temp_embeddings_path
    ).astype("float32")

    with temp_metadata_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        test_metadata = json.load(file)

    validate_updated_artifacts(
        test_metadata,
        test_embeddings,
        database_chunk_ids,
    )

    temp_embeddings_path.replace(
        EMBEDDINGS_PATH
    )

    temp_metadata_path.replace(
        METADATA_PATH
    )


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print()
    print("=" * 70)
    print(
        "TENNIS EXPLORE - "
        "INCREMENTAL EMBEDDING SYNCHRONIZATION"
    )
    print("=" * 70)

    print()
    print(
        "Loading existing production "
        "retrieval artifacts..."
    )

    metadata, embeddings = (
        load_existing_artifacts()
    )

    validate_existing_metadata(
        metadata
    )

    original_count = len(metadata)

    print(
        f"Existing metadata : {len(metadata)}"
    )

    print(
        f"Existing vectors  : {len(embeddings)}"
    )

    existing_chunk_ids = {
        item["chunk_db_id"]
        for item in metadata
    }

    print()
    print(
        "Checking shared PostgreSQL "
        "for chunk changes..."
    )

    database_chunk_ids = (
        load_database_chunk_ids()
    )

    database_chunk_id_set = set(
        database_chunk_ids
    )

    print(
        f"Database chunks   : "
        f"{len(database_chunk_ids)}"
    )

    # -----------------------------------------------------
    # DETECT NEW AND STALE CHUNKS
    # -----------------------------------------------------

    new_chunk_ids = [
        chunk_db_id
        for chunk_db_id in database_chunk_ids
        if chunk_db_id
        not in existing_chunk_ids
    ]

    stale_chunk_ids = [
        chunk_db_id
        for chunk_db_id in existing_chunk_ids
        if chunk_db_id
        not in database_chunk_id_set
    ]

    print(
        f"New chunks found  : "
        f"{len(new_chunk_ids)}"
    )

    print(
        f"Stale chunks found: "
        f"{len(stale_chunk_ids)}"
    )

    # -----------------------------------------------------
    # NOTHING TO UPDATE
    # -----------------------------------------------------

    if (
        not new_chunk_ids
        and not stale_chunk_ids
    ):
        print()
        print("=" * 70)
        print(
            "PRODUCTION RETRIEVAL ARTIFACTS "
            "ARE ALREADY UP TO DATE"
        )
        print("=" * 70)

        print()
        print(
            "No embeddings or metadata "
            "were changed."
        )

        return

    # -----------------------------------------------------
    # REMOVE STALE CHUNKS FIRST
    # -----------------------------------------------------

    working_metadata = metadata
    working_embeddings = embeddings

    if stale_chunk_ids:

        print()
        print(
            "Removing stale retrieval "
            "artifacts..."
        )

        (
            working_metadata,
            working_embeddings,
        ) = remove_stale_artifacts(
            working_metadata,
            working_embeddings,
            database_chunk_id_set,
        )

        print(
            f"Stale vectors removed : "
            f"{len(stale_chunk_ids)}"
        )

    # -----------------------------------------------------
    # LOAD AND EMBED NEW CHUNKS
    # -----------------------------------------------------

    new_embeddings_count = 0

    if new_chunk_ids:

        print()
        print(
            "Loading new chunks from "
            "shared PostgreSQL..."
        )

        new_chunks = load_new_chunks(
            new_chunk_ids
        )

        if len(new_chunks) != len(
            new_chunk_ids
        ):
            raise ValueError(
                "The number of loaded new chunks "
                "does not match the expected count."
            )

        print(
            f"New chunks loaded : "
            f"{len(new_chunks)}"
        )

        print()
        print(
            f"Loading embedding model: "
            f"{EMBEDDING_MODEL_NAME}"
        )

        model = SentenceTransformer(
            EMBEDDING_MODEL_NAME
        )

        texts = [
            chunk["text"]
            for chunk in new_chunks
        ]

        print()
        print(
            "Generating embeddings for "
            "new chunks only..."
        )

        new_embeddings = model.encode(
            texts,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        new_embeddings = (
            new_embeddings.astype("float32")
        )

        new_embeddings_count = len(
            new_embeddings
        )

        working_embeddings = np.concatenate(
            [
                working_embeddings,
                new_embeddings,
            ],
            axis=0,
        )

        next_vector_id = len(
            working_metadata
        )

        for offset, chunk in enumerate(
            new_chunks
        ):
            working_metadata.append(
                {
                    "vector_id":
                        next_vector_id + offset,
                    "chunk_db_id":
                        chunk["chunk_db_id"],
                    "chunk_id":
                        chunk["chunk_id"],
                    "source_file":
                        chunk["source_file"],
                    "file_type":
                        chunk["file_type"],
                    "page_number":
                        chunk["page_number"],
                    "slide_number":
                        chunk["slide_number"],
                    "word_count":
                        chunk["word_count"],
                    "text":
                        chunk["text"],
                }
            )

    # -----------------------------------------------------
    # FINAL VECTOR ID NORMALIZATION
    # -----------------------------------------------------

    for vector_id, item in enumerate(
        working_metadata
    ):
        item["vector_id"] = vector_id

    # -----------------------------------------------------
    # VALIDATE BEFORE SAVING
    # -----------------------------------------------------

    validate_updated_artifacts(
        working_metadata,
        working_embeddings,
        database_chunk_ids,
    )

    print()
    print("Validation passed.")

    print(
        "Saving synchronized production "
        "retrieval artifacts..."
    )

    # -----------------------------------------------------
    # SAFE SAVE
    # -----------------------------------------------------

    save_updated_artifacts(
        working_metadata,
        working_embeddings,
        database_chunk_ids,
    )

    # -----------------------------------------------------
    # SUMMARY
    # -----------------------------------------------------

    print()
    print("=" * 70)
    print(
        "INCREMENTAL SYNCHRONIZATION COMPLETE"
    )
    print("=" * 70)

    print(
        f"Previous vectors     : "
        f"{original_count}"
    )

    print(
        f"Stale vectors removed: "
        f"{len(stale_chunk_ids)}"
    )

    print(
        f"New vectors added    : "
        f"{new_embeddings_count}"
    )

    print(
        f"Total vectors        : "
        f"{len(working_embeddings)}"
    )

    print()
    print(
        "Production embeddings and metadata "
        "now exactly match PostgreSQL chunk IDs."
    )


if __name__ == "__main__":
    main()