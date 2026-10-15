
import base64
import os
import shutil
from pathlib import PurePosixPath
from uuid import uuid4
import subprocess
import tempfile
from pathlib import Path
import fitz
from fastapi.responses import Response

from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from backend.auth.deps import get_current_user_db, require_admin

router = APIRouter(prefix="/api/media", tags=["Media Library"])

BUCKET = os.getenv("MEDIA_S3_BUCKET", "tennis-explore-resources")
ROOT = "unstructured-data/"
UPLOAD_PREFIX = "unstructured-data/media-library-uploads/"
MAX_UPLOAD = 100 * 1024 * 1024

TYPES = {
    ".mp4": "video", ".mov": "video", ".webm": "video",
    ".jpg": "image", ".jpeg": "image", ".png": "image",
    ".webp": "image",
    ".pdf": "pdf", ".ppt": "document", ".pptx": "document",
    ".zip": "document",
}

MIME = {
    ".mp4": "video/mp4", ".mov": "video/quicktime",
    ".webm": "video/webm", ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg", ".png": "image/png",
    ".webp": "image/webp", ".pdf": "application/pdf",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".zip": "application/zip",
}


def encode_key(key):
    return base64.urlsafe_b64encode(key.encode()).decode().rstrip("=")


def decode_key(value):
    try:
        key = base64.urlsafe_b64decode(
            value + "=" * (-len(value) % 4)
        ).decode()
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(400, "Invalid media ID")

    if not key.startswith(ROOT) or key.endswith("/"):
        raise HTTPException(400, "Invalid media ID")
    return key


def storage_error(exc):
    raise HTTPException(502, "S3 storage request failed") from exc


@router.get("")
def list_media(
    category: str = Query("all", pattern="^(all|videos|images|documents)$"),
    search: str = Query("", max_length=200),
    limit: int = Query(24, ge=1, le=100),
    cursor: str | None = None,
    user=Depends(get_current_user_db),
):
    client = boto3.client("s3")
    items = []
    start_after = ""

    if cursor:
        start_after = decode_key(cursor)

    params = {
        "Bucket": BUCKET,
        "Prefix": ROOT,
        "MaxKeys": 1000,
    }
    if start_after:
        params["StartAfter"] = start_after

    last_key = start_after

    try:
        while True:
            response = client.list_objects_v2(**params)
            objects = response.get("Contents", [])

            for obj in objects:
                key = obj["Key"]
                last_key = key
                kind = TYPES.get(PurePosixPath(key).suffix.lower())

                if not kind or key.endswith("/"):
                    continue
                if category == "videos" and kind != "video":
                    continue
                if category == "images" and kind != "image":
                    continue
                if category == "documents" and kind not in ("pdf", "document"):
                    continue
                if search.casefold() not in PurePosixPath(key).name.casefold():
                    continue

                items.append({
                    "id": encode_key(key),
                    "title": PurePosixPath(key).name,
                    "type": kind,
                    "size_bytes": obj["Size"],
                    "last_modified": obj["LastModified"].isoformat(),
                })

                if len(items) >= limit:
                    return {
                        "items": items,
                        "next_cursor": encode_key(last_key),
                    }

            if not response.get("IsTruncated"):
                return {"items": items, "next_cursor": None}

            params["ContinuationToken"] = response["NextContinuationToken"]

    except (ClientError, BotoCoreError) as exc:
        storage_error(exc)


@router.get("/{media_id}/url")
def get_media_url(
    media_id: str,
    download: bool = False,
    user=Depends(get_current_user_db),
):
    key = decode_key(media_id)
    ext = PurePosixPath(key).suffix.lower()

    if ext not in TYPES:
        raise HTTPException(404, "Unsupported file")

    client = boto3.client("s3")

    try:
        client.head_object(Bucket=BUCKET, Key=key)
        url = client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": BUCKET,
                "Key": key,
                "ResponseContentType": MIME[ext],
                "ResponseContentDisposition": (
                    "attachment" if download else "inline"
                ),
            },
            ExpiresIn=900,
        )
        return {"url": url, "expires_in": 900}

    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in (
            "404", "NoSuchKey", "NotFound"
        ):
            raise HTTPException(404, "File not found") from exc
        storage_error(exc)
    except BotoCoreError as exc:
        storage_error(exc)


@router.post("/upload", status_code=201)
def upload_media(
    file: UploadFile = File(...),
    admin=Depends(require_admin),
):
    filename = PurePosixPath(
        (file.filename or "").replace("\\", "/")
    ).name
    ext = PurePosixPath(filename).suffix.lower()

    if ext not in TYPES or filename.startswith("."):
        raise HTTPException(400, "Unsupported file type")

    data = file.file.read(MAX_UPLOAD + 1)

    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "Maximum upload size is 100 MiB")
    if not data:
        raise HTTPException(400, "File is empty")

    key = f"{UPLOAD_PREFIX}{uuid4().hex}-{filename}"

    try:
        boto3.client("s3").put_object(
            Bucket=BUCKET,
            Key=key,
            Body=data,
            ContentType=MIME[ext],
        )
        return {
            "id": encode_key(key),
            "title": filename,
            "type": TYPES[ext],
        }
    except (ClientError, BotoCoreError) as exc:
        storage_error(exc)

@router.get("/{media_id}/preview")
def preview_powerpoint(
    media_id: str,
    user=Depends(get_current_user_db),
):
    key = decode_key(media_id)
    ext = PurePosixPath(key).suffix.lower()

    if ext not in (".ppt", ".pptx"):
        raise HTTPException(
            status_code=400,
            detail="Preview conversion supports PowerPoint files only",
        )

    soffice = (
        os.getenv("LIBREOFFICE_PATH")
        or shutil.which("libreoffice")
        or shutil.which("soffice")
        or (
            "/Applications/LibreOffice.app/Contents/MacOS/soffice"
            if os.path.isfile("/Applications/LibreOffice.app/Contents/MacOS/soffice")
            else None
        )
    )

    if not soffice or not os.path.isfile(soffice):
        raise HTTPException(
            status_code=503,
            detail="LibreOffice is not installed or configured",
        )

    temp_dir = tempfile.TemporaryDirectory(prefix="tennis-preview-")
    workdir = Path(temp_dir.name)
    source = workdir / f"presentation{ext}"
    pdf = workdir / "presentation.pdf"

    try:
        client = boto3.client("s3")

        # Limit conversion input to 50 MiB.
        metadata = client.head_object(Bucket=BUCKET, Key=key)

        if metadata["ContentLength"] > 50 * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail="PowerPoint file is too large to preview",
            )

        client.download_file(BUCKET, key, str(source))

        result = subprocess.run(
            [
                soffice,
                "-env:UserInstallation=file://" + str(workdir / "lo-profile"),
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(workdir),
                str(source),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0 or not pdf.exists():
            raise HTTPException(
                status_code=500,
                detail="PowerPoint conversion failed",
            )

        return FileResponse(
            path=str(pdf),
            media_type="application/pdf",
            filename="preview.pdf",
            content_disposition_type="inline",
            background=BackgroundTask(temp_dir.cleanup),
        )

    except subprocess.TimeoutExpired as exc:
        raise HTTPException(
            status_code=504,
            detail="PowerPoint conversion timed out",
        ) from exc

    except (ClientError, BotoCoreError) as exc:
        storage_error(exc)

    finally:
        # Keep temporary files until FileResponse finishes sending.
        # On errors, clean up immediately.
        if "result" not in locals() or result.returncode != 0 or not pdf.exists():
            temp_dir.cleanup()


@router.get("/{media_id}/thumbnail")
def get_media_thumbnail(
    media_id: str,
    user=Depends(get_current_user_db),
):
    key = decode_key(media_id)
    ext = PurePosixPath(key).suffix.lower()

    if ext not in (".pdf", ".ppt", ".pptx"):
        raise HTTPException(
            status_code=400,
            detail="Thumbnail not supported for this file type",
        )

    # Limit files to 50 MiB for thumbnail generation.
    client = boto3.client("s3")

    try:
        metadata = client.head_object(Bucket=BUCKET, Key=key)

        if metadata["ContentLength"] > 50 * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail="File is too large for thumbnail generation",
            )

        with tempfile.TemporaryDirectory(prefix="tennis-thumb-") as folder:
            workdir = Path(folder)
            source = workdir / f"document{ext}"
            pdf = workdir / "document.pdf"

            client.download_file(BUCKET, key, str(source))

            if ext in (".ppt", ".pptx"):
                soffice = (
                    # Keep your existing LibreOffice path configuration here
                )

                if not soffice or not os.path.isfile(soffice):
                    raise HTTPException(
                        status_code=503,
                        detail="LibreOffice is not installed or configured",
                    )

                try:
                    result = subprocess.run(
                        [
                            soffice,
                            "-env:UserInstallation=file://" + str(workdir / "lo-profile"),
                            "--headless",
                            "--convert-to", "pdf",
                            "--outdir", str(workdir),
                            str(source),
                        ],
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )
                except subprocess.TimeoutExpired as exc:
                    raise HTTPException(
                        status_code=504,
                        detail="Thumbnail conversion timed out",
                    ) from exc

                if result.returncode != 0 or not pdf.exists():
                    raise HTTPException(
                        status_code=500,
                        detail="Thumbnail conversion failed",
                    )

            else:
                pdf = source

            try:
                with fitz.open(str(pdf)) as document:
                    if document.page_count == 0:
                        raise HTTPException(422, "Document has no pages")

                    page = document.load_page(0)
                    scale = min(1.5, 900 / max(page.rect.width, 1))
                    pixmap = page.get_pixmap(
                        matrix=fitz.Matrix(scale, scale),
                        alpha=False,
                    )
                    image_data = pixmap.tobytes("png")

            except (fitz.FileDataError, fitz.EmptyFileError) as exc:
                raise HTTPException(
                    status_code=422,
                    detail="Cannot render this document",
                ) from exc

            return Response(
                content=image_data,
                media_type="image/png",
                headers={"Cache-Control": "private, max-age=300"},
            )

    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in (
            "404", "NoSuchKey", "NotFound"
        ):
            raise HTTPException(404, "File not found") from exc
        storage_error(exc)

    except BotoCoreError as exc:
        storage_error(exc)