# scripts/FastAPI/rag_service.py

from __future__ import annotations

import os
from pathlib import Path

from deep_translator import GoogleTranslator
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langdetect import detect
from mlx_lm import generate, load

load_dotenv()

# --- init (максимально просто: один раз при импорте) ---
CHUNKS_DIR = Path(os.environ["MOODLE_CHUNKS_DIR"])  # если не нужен, можно удалить
PERSIST_DIR = os.environ["MOODLE_CHROMA_DB_DIR"]
COLLECTION_NAME = os.environ.get("MOODLE_COLLECTION_NAME", "moodle_docs")

hf_embeddings = HuggingFaceBgeEmbeddings(
    model_name="BAAI/bge-base-en-v1.5",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)

vector_store = Chroma(
    collection_name=COLLECTION_NAME,
    embedding_function=hf_embeddings,
    persist_directory=PERSIST_DIR,
)

model, tokenizer = load("mlx-community/Qwen2.5-7B-Instruct-4bit")  # type: ignore[misc]


# --- функции из ноутбука ---
def prepare_query(user_query: str) -> tuple[str, str]:
    text = (user_query or "").strip()
    if not text:
        return "", "ru"

    try:
        lang = detect(text)
    except Exception:
        lang = "ru"

    if lang not in ("ru", "en"):
        lang = "en"

    if lang == "ru":
        try:
            query_en = GoogleTranslator(source="ru", target="en").translate(text)
            if not query_en:
                query_en = text
        except Exception:
            query_en = text
    else:
        query_en = text

    return query_en, lang


def build_context(user_query: str, k: int = 5) -> tuple[str, str, list[tuple]]:  # type: ignore[type-arg]
    query_en, user_lang = prepare_query(user_query)
    results = vector_store.similarity_search_with_score(query_en, k=k)

    context_blocks = []
    for i, (doc, score) in enumerate(results, 1):
        context_blocks.append(
            f"[{i}]\n"
            f"doc_title: {doc.metadata.get('doc_title', 'unknown')}\n"
            f"distance: {float(score):.4f}\n"
            f"source_links: {doc.metadata.get('source_links', [])}\n"
            f"youtube_links: {doc.metadata.get('youtube_links', [])}\n"
            f"text:\n{doc.page_content}"
        )

    context = "\n\n---\n\n".join(context_blocks)
    return context, user_lang, results


def generate_answer(
    user_query: str,
    context: str,
    user_lang: str,
    recent_history: list[dict[str, str]] | None = None,
) -> str:
    answer_lang = "Russian" if user_lang == "ru" else "English"

    system_prompt = f"""
    <ROLE_DEFINITION>
    You are the official Moodle documentation assistant acting as a technical consultant.
    </ROLE_DEFINITION>

    <MAIN_TASK_GUIDELINES>
    Your task is to provide precise, formal, and verifiable answers strictly based on the provided CONTEXT.
    You must directly answer the user’s question without adding external knowledge.
    If the answer is not present in the CONTEXT, respond exactly: "Not found in the documentation".
    Do not make assumptions, interpretations, or extrapolations beyond the CONTEXT.
    The response must be structured and concise.
    </MAIN_TASK_GUIDELINES>

    <IMPORTANT_LANGUAGE_GUIDELINES>
    Determine the language of the user's query and use THAT SAME language for:
    - all actions,
    - all search formulations,
    - the final answer,
    - all textual fields and outputs.

    Answer strictly in {answer_lang}.

    If the query is in Russian — all fields and responses must be strictly in Russian.
    If the query is in English — all fields and responses must be strictly in English.
    </IMPORTANT_LANGUAGE_GUIDELINES>

    <OUTPUT_FORMAT_REQUIREMENTS>
    The ending section is mandatory and must always be included:

    - source_links: [list of links from CONTEXT]
    - youtube_links: [list of links from CONTEXT if available; if none — write "none"]
    </OUTPUT_FORMAT_REQUIREMENTS>
    """.strip()

    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

    if recent_history:
        for m in recent_history:
            if not isinstance(m, dict):
                continue
            role = m.get("role")
            content = m.get("content")
            if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
                messages.append({"role": role, "content": content})

    messages.append(
        {
            "role": "user",
            "content": (f"QUESTION:\n{user_query}\n\nCONTEXT:\n{context}\n\nIMPORTANT: Respond ONLY in {answer_lang}."),
        }
    )

    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return generate(model, tokenizer, prompt=prompt, max_tokens=550)


def retrieval_query_with_context(query: str, chat_history: list[dict[str, str]]) -> str:
    q = query.strip()
    if len(q.split()) <= 4:
        prev_users = [m["content"] for m in chat_history if m.get("role") == "user"]
        if prev_users:
            return prev_users[-1] + "\n" + q
    return q
