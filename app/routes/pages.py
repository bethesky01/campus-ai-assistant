from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import ROOT_DIR

router = APIRouter()
templates = Jinja2Templates(directory=str(ROOT_DIR / "app" / "templates"))


@router.get("/", response_class=HTMLResponse)
def student_page(request: Request):
    return templates.TemplateResponse(request=request, name="chat.html")
