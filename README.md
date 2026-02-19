# Moodle RAG (Crawler + Knowledge Base + FastAPI)

Проект собирает документацию Moodle, очищает ее, режет на чанки, индексирует в векторную БД и отвечает на вопросы через RAG API.

## Что делает проект

1. Краулит страницы Moodle Docs (`docs.moodle.org`) через `crawl4ai`.
2. Сохраняет сырые данные (`pages.jsonl`, `images.jsonl`, `youtube_links.jsonl`, `errors.jsonl`).
3. Очищает markdown и формирует читабельный корпус (`clean_markdown` + `pages.cleaned.jsonl`).
4. Делит документы на чанки (`chunks_md`) для векторного поиска.
5. FastAPI-сервис:
   - делает retrieval по Chroma,
   - собирает контекст,
   - генерирует ответ через `mlx-lm` (Qwen2.5-7B-Instruct-4bit),
   - возвращает ответ и ссылки на источники.

## Требования

- Python `>= 3.12`
- Рекомендуется `uv` для управления окружением
- Playwright/Chromium для краулера
- Для генерации ответа используется `mlx-lm` (обычно macOS Apple Silicon)

## Зависимости

Основные зависимости (см. `pyproject.toml`):

- `crawl4ai`, `playwright`, `chromium`
- `langchain-chroma`, `langchain-community`, `langchain-text-splitters`
- `sentence-transformers`, `torch`
- `mlx-lm`
- `fastapi`, `uvicorn`
- `python-dotenv`, `deep-translator`, `langdetect`, `pandas`

## Установка

### Вариант 1 (рекомендуется): через `uv`

```bash
uv sync
```

### Вариант 2: через `pip`

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Установить браузер для Playwright:

```bash
playwright install chromium
```

## Переменные окружения

Файл `.env` должен содержать:

```env
MOODLE_CHUNKS_DIR=data/moodle_docs/chunks_md
MOODLE_CHROMA_DB_DIR=data/moodle_docs/chroma_langchain_db
MOODLE_COLLECTION_NAME=moodle_docs
```

Используются в `scripts/FastAPI/rag_service.py`.

## Запуск пайплайна данных

### 1) Краулинг Moodle Docs

```bash
python scripts/moodle_docs_crawler.py \
  --start-url "https://docs.moodle.org/403/en/Main_page" \
  --docs-prefix "/403/en/" \
  --out-dir "data/moodle_docs" \
  --max-pages 200 \
  --max-concurrent 3 \
  --delay-seconds 0.5
```

Опционально:
- `--with-screenshots`
- `--cookies-file` (cookies array или Playwright storage_state JSON)
- `--user-agent`

### 2) Очистка и сбор markdown-корпуса

```bash
python scripts/prepare_markdown_corpus.py \
  --input data/moodle_docs/pages.jsonl \
  --output-jsonl data/moodle_docs/pages.cleaned.jsonl \
  --output-md-dir data/moodle_docs/clean_markdown
```

### 3) Нарезка на чанки

```bash
python scripts/chunk_clean_markdown.py \
  --input-dir data/moodle_docs/clean_markdown \
  --output-dir data/moodle_docs/chunks_md \
  --chunk-size 1100 \
  --chunk-overlap 160
```

### 4) Индексация в Chroma

В репозитории нет отдельного `.py` для индексации; используется ноутбук:

- `scripts/Notebooks/create_vectorDB.ipynb`

Перед запуском API БД Chroma должна быть уже создана и содержать коллекцию `MOODLE_COLLECTION_NAME`.

## Запуск API

```bash
uvicorn scripts.FastAPI.main:app --reload
```

Проверка:

```bash
curl -X GET "http://127.0.0.1:8000/health"
```

Пример запроса к чату:

```bash
curl -X POST "http://127.0.0.1:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Как включить completion tracking в курсе?",
    "history": [],
    "k": 5
  }'
```

## Структура проекта

```text
.
├── data/
│   └── moodle_docs/
│       ├── pages.jsonl                # сырые страницы
│       ├── pages.cleaned.jsonl        # очищенные записи
│       ├── images.jsonl
│       ├── youtube_links.jsonl
│       ├── errors.jsonl
│       ├── clean_markdown/            # очищенные .md
│       ├── chunks_md/                 # чанки документов
│       └── chroma_langchain_db/       # векторная БД Chroma
├── scripts/
│   ├── moodle_docs_crawler.py         # краулер
│   ├── prepare_markdown_corpus.py     # очистка и сбор корпуса
│   ├── chunk_clean_markdown.py        # нарезка на чанки
│   ├── bootstrap_storage_state.py     # помощь с Cloudflare challenge/state
│   ├── FastAPI/
│   │   ├── main.py                    # FastAPI endpoints
│   │   └── rag_service.py             # retrieval + generation
│   └── Notebooks/
│       ├── create_chunks.ipynb
│       ├── create_vectorDB.ipynb
│       └── rag.ipynb
├── pyproject.toml
├── uv.lock
└── .env
```

## Эндпоинты API

- `GET /health` -> статус сервиса.
- `POST /chat` -> ответ модели + `source_links` + `youtube_links`.

Тело `POST /chat`:

```json
{
  "message": "string",
  "history": [{"role": "user|assistant", "content": "string"}],
  "k": 5
}
```

## Важные замечания

- Модель и векторное хранилище инициализируются при импорте `rag_service.py`; первый запуск может быть долгим.
- `MOODLE_CHROMA_DB_DIR` и коллекция должны существовать до старта API.
- Если Moodle Docs отдает challenge-страницы, используйте `scripts/bootstrap_storage_state.py` и передавайте state/cookies в краулер.

