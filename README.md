# Moodle RAG – Retrieval-Augmented Generation System

Полнофункциональная система Retrieval-Augmented Generation (RAG) для Moodle документации. Система поддерживает **два конкурирующих embedding-подхода** для сравнения качества поиска и включает интерактивный чатбот на базе локальной LLM.

## 🎯 Возможности

- **Двойная система эмбеддингов**: BGE (BAAI/bge-base-en-v1.5) и PPLX (pplx-embed-v1-0.6b)
- **ChromaDB векторная база** с поддержкой контекстных эмбеддингов (PPLX)
- **Локальная LLM** (Qwen2.5-7B-Instruct-4bit через MLX) для генерации ответов
- **Мультиязычная поддержка**: русский + английский (с автоматическим переводом для BGE, без перевода для PPLX)
- **RAG для двух моделей**: `rag.ipynb` (BGE) и `rag_pplx.ipynb` (PPLX)
- **Сравнение моделей**: метрики Hit Rate @K и MRR для оценки качества поиска
- **Eval-блоки** с LLM-as-judge для проверки faithfulness и attribution ответов

## 📋 Структура проекта

```
Moodle_RAG/
├── data/
│   └── moodle_docs/
│       ├── clean_markdown/          # Чистые MD документы
│       └── chunks_md/               # Чанки документов по 2KB
├── scripts/
│   ├── pplx_embed/
│   │   ├── __init__.py
│   │   └── pplx_embed.py           # PplxEmbedFunction, PplxContextEmbedFunction
│   └── Notebooks/
│       ├── create_vectorDB.ipynb    # Построение BGE векторной БД
│       ├── vectordb_with_context.ipynb # Построение PPLX с контекстом
│       ├── rag.ipynb                # RAG чатбот на BGE
│       ├── rag_pplx.ipynb           # RAG чатбот на PPLX
│       ├── compare_embeddings.ipynb # Сравнение BGE vs PPLX
│       ├── pplx_chunks.ipynb        # Тестирование PPLX коллекции
│       └── chroma_db_pplx/          # PPLX ChromaDB (игнорируется в git)
├── pyproject.toml
├── uv.lock
└── README.md
```

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
# Используем uv для быстрой установки
uv sync

# Или через pip
pip install -r requirements.txt
```

### 2. Переменные окружения

Создайте `.env` файл:

```bash
# Пути к данным
MOODLE_CHUNKS_DIR="/Users/sergey/Desktop/Moodle_RAG/data/moodle_docs/chunks_md"
MOODLE_CHROMA_DB_DIR="/Users/sergey/Desktop/Moodle_RAG/scripts/Notebooks/chroma_db_bge"
MOODLE_COLLECTION_NAME="moodle_docs"

# OpenAI (опционально, если используется OpenAI вместо MLX)
OPENAI_API_KEY="sk-..."
OPENAI_MODEL="gpt-4o-mini"
```

### 3. Построение векторных БД

**BGE (LangChain Chroma):**
```bash
jupyter notebook scripts/Notebooks/create_vectorDB.ipynb
```

**PPLX (ChromaDB с контекстом):**
```bash
jupyter notebook scripts/Notebooks/vectordb_with_context.ipynb
```

### 4. Запуск RAG чатбота

**На BGE эмбеддингах:**
```bash
jupyter notebook scripts/Notebooks/rag.ipynb
```
- Автоматический перевод русских запросов на английский
- Ответы на русском/английском в зависимости от языка запроса
- Поддержка follow-up вопросов (short queries)

**На PPLX эмбеддингах:**
```bash
jupyter notebook scripts/Notebooks/rag_pplx.ipynb
```
- Прямой поиск без перевода (мультиязычная модель)
- Контекстные эмбеддинги (лучше для семантики)
- Быстрее на CPU

### 5. Сравнение моделей

```bash
jupyter notebook scripts/Notebooks/compare_embeddings.ipynb
```

**Результаты сравнения на 10 тестовых запросах:**

| Метрика | BGE | PPLX |
|---------|-----|------|
| Hit Rate @5 | 90.0% | **100.0%** ✅ |
| MRR @5 | 0.850 | **1.000** ✅ |

**Вывод**: PPLX превосходит BGE по качеству поиска, особенно на мультиязычных запросах.

## 📚 Компоненты

### `scripts/pplx_embed/__init__.py`
Экспортирует embedding-функции:
- `PplxEmbedFunction()` – для queries
- `PplxContextEmbedFunction()` – для chunks с контекстом документа

### `rag.ipynb` (BGE-версия)
1. **Retrieval**: `similarity_search_with_score()` с переводом запроса (GoogleTranslator)
2. **Context building**: Собирает top-5 с метаданными (doc_title, source_links, youtube_links)
3. **Generation**: Qwen2.5-7B-Instruct-4bit (MLX) с промптом на нужном языке
4. **Evaluation**: Hit@K, MRR, LLM-judge faithfulness

### `rag_pplx.ipynb` (PPLX-версия)
1. **Retrieval**: `collection.query()` без перевода (мультиязычная)
2. **Context building**: Контекстные эмбеддинги (см. `PplxContextEmbedFunction`)
3. **Generation**: Qzen2.5-7B-Instruct-4bit
4. **Evaluation**: Идентичные метрики

### `compare_embeddings.ipynb`
Сравнивает качество обеих моделей:
- **Hit Rate @K**: доля запросов с релевантным результатом в top-K
- **MRR @K**: средний обратный ранг первого релевантного результата
- **Ground truth**: вручную подобранные ожидаемые источники

## 🔧 Архитектура RAG Pipeline

```
User Query (RU/EN)
    ↓
[BGE Path]                      [PPLX Path]
    ↓                                ↓
GoogleTranslator (RU→EN)        No translation
    ↓                                ↓
similarity_search_with_score    collection.query()
    ↓                                ↓
Top-5 documents                 Top-5 documents
(distance: 0-1)                (distance: 0-2)
    ↓                                ↓
Build Context                   Build Context
    ↓                                ↓
LLM Prompt (detect lang)        LLM Prompt (detect lang)
    ↓                                ↓
Qwen2.5-7B-Instruct-4bit        Qwen2.5-7B-Instruct-4bit
    ↓                                ↓
Answer (RU/EN)                  Answer (RU/EN)
```

## 📊 Метрики Evaluation

### Retrieval Metrics
- **Hit Rate @K** – (# queries с hit) / (всего queries)
- **MRR @K** – mean(1/rank_of_first_hit) или 0 если нет hit

### Generation Metrics
- **Faithfulness (LLM-Judge)** – проверяет, что ответ поддержан контекстом
- **Source Attribution** – совпадают ли цитируемые источники с retrieved documents
- **Exact Match** – точность метаданных (doc_title, links)

## 🗂️ Данные и Индексирование

### Чанкирование
- **Размер чанка**: 2KB
- **Оверлей**: 200 символов между соседними чанками
- **Метаданные**: doc_title, source_file, chunk_index, h1, h2, h3, links

### PPLX Context Embeddings
```python
# Каждый чанк эмбеддируется с контекстом полного документа:
embeddings = ctx_embed.embed_with_context(chunks, full_document)

# Это улучшает качество поиска, понимая семантику в контексте документа
```

### Размеры коллекций
| Model | Collection | Chunks | Size |
|-------|-----------|--------|------|
| BGE | moodle_docs | 2,697 | ~500MB |
| PPLX | moodle_docs_pplx | 3,395 | ~650MB |

## 🎮 Использование

### Интерактивный чатбот BGE
```python
# scripts/Notebooks/rag.ipynb
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceBgeEmbeddings

# Загружается из persistence_dir
continual_chat(k=5, history_turns=3)
# ВЫ: Как создать новый курс?
# ✅ Ответ AI: [ответ на русском с источниками]
```

### Интерактивный чатбот PPLX
```python
# scripts/Notebooks/rag_pplx.ipynb
import chromadb
from scripts.pplx_embed import PplxEmbedFunction

# Загружается из chroma_db_pplx
continual_chat(k=5, history_turns=3)
# ВЫ: How to set up gradebook?
# ✅ Ответ AI: [ответ на английском с источниками]
```

### Programmatic Retrieval
```python
# BGE
docs = vector_store.similarity_search_with_score("query", k=5)
for doc, score in docs:
    print(f"{doc.metadata['doc_title']} (sim={1-score:.4f})")

# PPLX
results = collection.query(query_texts=["query"], n_results=5)
for meta, dist, text in zip(results["metadatas"][0], 
                             results["distances"][0], 
                             results["documents"][0]):
    print(f"{meta['source']} (dist={dist:.4f})")
```

## 🐛 Troubleshooting

### Import Error: `cannot import name 'PplxEmbedFunction'`
**Решение**: Убедитесь, что используется относительный импорт в `__init__.py`:
```python
# scripts/pplx_embed/__init__.py
from .pplx_embed import PplxEmbedFunction, PplxContextEmbedFunction
```

### ChromaDB Deprecation Warnings
Игнорируйте предупреждения о `torch_dtype` и `input_embeds` – это internal warnings от transformers.

### OutOfMemory на CPU
Если PPLX embeddings медленно:
- Используйте `device='cpu'` (по умолчанию)
- Уменьшите batch_size в `embed_with_context()`
- Запустите на GPU если доступен: `device='cuda'`

## 📖 Документация моделей

### BGE (BAAI/bge-base-en-v1.5)
- **Язык**: English only (требует перевода для RU)
- **Размер**: 109M параметров
- **Латентность**: ~50ms на 1000 документов
- **Точность**: 93.2% на MTEB benchmark

### PPLX (pplx-embed-v1-0.6b)
- **Язык**: Мультиязычная (RU, EN, ZH, ES, FR, ...)
- **Размер**: 600M параметров
- **Латентность**: ~100ms на 1000 документов
- **Особенность**: Поддерживает контекстные эмбеддинги через `embed_with_context()`

## 🤝 Contributing

1. Создайте ветку: `git checkout -b feature/my-feature`
2. Коммитьте изменения: `git commit -m "feat: add feature"`
3. Push на GitHub: `git push origin feature/my-feature`
4. Откройте PR

## 📝 Лицензия

MIT License – см. LICENSE файл.

