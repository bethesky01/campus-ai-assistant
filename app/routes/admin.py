import logging
import asyncio
import json

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from app.config import ROOT_DIR
from app.models.schemas import CATEGORIES, DocumentMetadata
from app.services.document_service import DocumentService

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory=str(ROOT_DIR / "app" / "templates"))
logger = logging.getLogger(__name__)


@router.get("", response_class=HTMLResponse)
def admin_page(request: Request):
    documents = DocumentService().list_documents()
    return templates.TemplateResponse(request=request, name="admin.html", context={
        "documents": documents, "categories": CATEGORIES,
        "indexed_count": sum(d.status == "indexed" for d in documents),
        "total_chunks": sum(d.chunk_count for d in documents),
    })


@router.get("/documents", response_model=list[DocumentMetadata])
def documents():
    return DocumentService().list_documents()


@router.post("/upload", response_model=DocumentMetadata, status_code=201)
async def upload(title: str = Form(...), category: str = Form(...), file: UploadFile = File(...)):
    try:
        return await DocumentService().upload(title, category, file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Upload failed")
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/upload/progress")
async def upload_with_progress(
    title: str = Form(...), category: str = Form(...), file: UploadFile = File(...),
):
    """Stream actual ingestion stages to the admin UI as server-sent events."""
    async def events():
        queue: asyncio.Queue[dict] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def report(stage: str, percent: int, message: str) -> None:
            event = {"type": "progress", "stage": stage, "percent": percent, "message": message}
            loop.call_soon_threadsafe(queue.put_nowait, event)

        async def process() -> None:
            try:
                result = await DocumentService().upload(title, category, file, progress=report)
                await queue.put({"type": "result", "document": result.model_dump(mode="json")})
            except Exception as exc:
                logger.exception("Progress upload failed")
                await queue.put({"type": "error", "message": str(exc)})
            finally:
                await queue.put({"type": "done"})

        task = asyncio.create_task(process())
        try:
            while True:
                event = await queue.get()
                yield f"data: {json.dumps(event)}\n\n"
                if event["type"] == "done":
                    break
        finally:
            await task

    return StreamingResponse(
        events(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/documents/{document_id}/reindex", response_model=DocumentMetadata)
def reindex(document_id: str):
    try:
        return DocumentService().reindex(document_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Re-index failed")
        raise HTTPException(status_code=503, detail=f"Re-indexing failed: {exc}") from exc


@router.delete("/documents/{document_id}", status_code=204)
def delete(document_id: str):
    try:
        DocumentService().delete(document_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Deletion failed")
        raise HTTPException(status_code=503, detail="The document could not be deleted.") from exc
