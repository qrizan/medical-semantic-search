import re
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .engine import semantic_search 
import logging
import asyncio

logger = logging.getLogger(__name__)

app = FastAPI(title="Medical Semantic Search")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# custom Jinja2 filter untuk highlight keywords
# highlight keywords dari query di dalam text
def highlight_keywords(text, query):
    if not query or not text:
        return text
    words = query.lower().split()
    result = text
    for word in words:
        
        # case-insensitive replace dengan mark tag
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        result = pattern.sub(lambda m: f"<mark>{m.group()}</mark>", result)
    return result

# register filter ke Jinja2
templates.env.filters['highlight_keywords'] = highlight_keywords


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, q: str = ""):
    results = []
    error_message = None
    
    if q.strip():
        try:
            # jalankan semantic_search di thread pool dengan timeout
            # menggunakan asyncio.to_thread untuk Python 3.9+
            # jika Python 3.8, gunakan: loop.run_in_executor(None, semantic_search, q.strip())
            results = await asyncio.wait_for(
                asyncio.to_thread(semantic_search, q.strip()),
                timeout=25.0  # 25 detik timeout
            )
        except asyncio.TimeoutError:
            logger.error("Semantic search timeout after 25 seconds")
            error_message = "Request timeout — proses pencarian memakan waktu terlalu lama."
        except Exception as e:
            logger.error(f"Error in semantic_search: {e}", exc_info=True)
            error_message = f"Terjadi kesalahan: {str(e)}"
    
    # cek apakah request dari HTMX (hanya return results)
    if request.headers.get("HX-Request") == "true":
        if error_message:
            
            # return error state untuk HTMX
            return HTMLResponse(
                f'<div class="error-state">'
                f'<div class="error-icon">⚠️</div>'
                f'<p>{error_message}</p>'
                f'<p class="error-sub">Silakan coba lagi.</p>'
                f'</div>'
            )
        return templates.TemplateResponse("results.html", {
            "request": request,
            "query": q,
            "results": results
        })
    
    # request normal (return full page)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "query": q,
        "results": results,
        "error_message": error_message
    })