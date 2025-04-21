from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import os

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def root():
    html_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../client_test.html"))
    with open(html_file_path, "r") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)
