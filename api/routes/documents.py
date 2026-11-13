from pathlib import Path
from typing import Literal
from fastapi import APIRouter, HTTPException, Request
from starlette.concurrency import run_in_threadpool
from ingestion.ocr import extract_upload, OcrUnavailable

from api.data_store import documents

router = APIRouter(prefix="/documents", tags=["documents"])

@router.get("/")
def list_documents():
    return {"items": documents(), "total": len(documents())}


@router.post("/ocr")
async def preview_ocr(request: Request, filename: str, mode: Literal["auto", "force"] = "auto"):
    extension = Path(filename).suffix.lower().lstrip(".")
    if extension not in {"pdf", "png", "jpg", "jpeg"}:
        raise HTTPException(415, "Choose a PDF, PNG, or JPEG file.")
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > 20 * 1024 * 1024:
            raise HTTPException(413, "Choose a file smaller than 20 MB.")
    if not content:
        raise HTTPException(400, "The uploaded file is empty.")
    try:
        return await run_in_threadpool(extract_upload, bytes(content), extension, mode == "force")
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    except OcrUnavailable as error:
        raise HTTPException(503, str(error)) from error
    except Exception as error:
        raise HTTPException(400, "The document could not be read. Check the file and try again.") from error
