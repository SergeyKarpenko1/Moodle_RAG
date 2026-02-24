import time
from collections.abc import Callable

from fastapi.responses import Response
from pydantic import BaseModel, Field

from fastapi import FastAPI, Request
from scripts.FastAPI.rag_service import (
    build_context,
    generate_answer,
    retrieval_query_with_context,
)

app = FastAPI(title="Moodle RAG API", version="0.1.0")


class ChatRequest(BaseModel):
    message: str
    history: list[dict[str, str]] = Field(default_factory=list)
    k: int = 5


class ChatResponse(BaseModel):
    answer: str
    source_links: list[str]
    youtube_links: list[str]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.middleware("http")
async def simple_middleware(request: Request, call_next: Callable) -> Response:  # type: ignore[type-arg]
    start = time.time()

    response = await call_next(request)

    process_time = time.time() - start
    response.headers["X-Process-Time"] = f"{process_time:.4f}"
    print(f"{request.method} {request.url.path} -> {response.status_code} ({process_time:.4f}s)")

    return response  # type: ignore[no-any-return]


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    rq = retrieval_query_with_context(payload.message, payload.history)
    context, user_lang, results = build_context(rq, k=payload.k)
    answer = generate_answer(
        payload.message,
        context,
        user_lang,
        recent_history=payload.history[-6:],
    )

    source_links: list[str] = []
    youtube_links: list[str] = []
    for doc, _ in results:
        source_links.extend(doc.metadata.get("source_links", []) or [])
        youtube_links.extend(doc.metadata.get("youtube_links", []) or [])

    return ChatResponse(
        answer=answer,
        source_links=sorted(set(source_links)),
        youtube_links=sorted(set(youtube_links)),
    )


# uvicorn scripts.FastAPI.main:app --reload
