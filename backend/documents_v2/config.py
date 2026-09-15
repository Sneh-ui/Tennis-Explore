from pathlib import Path


# =========================================================
# BASE PROJECT DIRECTORY
# =========================================================

# Location of the documents_v2 folder
BASE_DIR = Path(__file__).resolve().parent


# =========================================================
# OUTPUT DIRECTORIES
# =========================================================

OUTPUT_DIR = BASE_DIR / "outputs"

INVENTORY_OUTPUT_DIR = OUTPUT_DIR / "inventory"

EXTRACTION_OUTPUT_DIR = OUTPUT_DIR / "extracted"


# Create output folders automatically if they do not exist
OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

INVENTORY_OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

EXTRACTION_OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =========================================================
# LOCAL TEST DATA
# =========================================================

TEST_DATA_DIR = BASE_DIR / "test_data"

PDF_TEST_DIR = TEST_DATA_DIR / "pdf"

PPTX_TEST_DIR = TEST_DATA_DIR / "pptx"


# =========================================================
# AWS S3 CONFIGURATION
# =========================================================

# We will configure the real bucket after the client
# provides approved programmatic access.

S3_BUCKET_NAME = "tennis-explore-resources"

S3_DOCUMENT_PREFIX = (
    "unstructured-data/document-resources/"
)

PDF_PREFIX = (
    "unstructured-data/"
    "document-resources/"
    "research-pdfs/"
)

PPTX_PREFIX = (
    "unstructured-data/"
    "document-resources/"
    "powerpoint-folder/"
)


# =========================================================
# INVENTORY OUTPUT FILES
# =========================================================

INVENTORY_CSV = (
    INVENTORY_OUTPUT_DIR
    / "production_inventory.csv"
)

INVENTORY_SUMMARY_CSV = (
    INVENTORY_OUTPUT_DIR
    / "production_inventory_summary.csv"
)

REPRESENTATIVE_SAMPLE_CSV = (
    INVENTORY_OUTPUT_DIR
    / "representative_samples.csv"
)


# =========================================================
# SAMPLE SETTINGS
# =========================================================

REPRESENTATIVE_SAMPLE_COUNT = 8
CHUNK_OUTPUT_DIR = OUTPUT_DIR / "chunks"

CHUNK_OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

# =========================================================
# EMBEDDING OUTPUT
# =========================================================

EMBEDDING_OUTPUT_DIR = OUTPUT_DIR / "embeddings"

EMBEDDING_OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =========================================================
# FAISS OUTPUT
# =========================================================

FAISS_OUTPUT_DIR = OUTPUT_DIR / "faiss"

FAISS_OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =========================================================
# EMBEDDING SETTINGS
# =========================================================

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

RERANKER_MODEL_NAME = "BAAI/bge-reranker-base"

OLLAMA_MODEL_NAME = "mistral"
OLLAMA_URL = "http://localhost:11434/api/generate"