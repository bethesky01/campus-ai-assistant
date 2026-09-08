import logging
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatRequest, ChatResponse
from app.services.assistant_service import AssistantService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest):
    try:
        return AssistantService().respond(payload.question, payload.session_id)
    except Exception as exc:
        logger.exception("Chat request failed")
        message = "The local AI service is unavailable. Check Ollama and the configured models."
        if "no documents" in str(exc).lower():
            message = "The knowledge base is empty. Ask an administrator to upload a document."
        raise HTTPException(status_code=503, detail=message) from exc


@router.post("/chat/stream")
def chat_stream(payload: ChatRequest):
    def events():
        try:
            for event in AssistantService().stream(payload.question, payload.session_id):
                yield f"event: {event['event']}\ndata: {json.dumps(event)}\n\n"
        except Exception:
            logger.exception("Streaming chat request failed")
            yield f"event: error\ndata: {json.dumps({'event': 'error', 'message': 'The assistant could not complete this response.'})}\n\n"
    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
