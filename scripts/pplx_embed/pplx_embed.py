import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer
from chromadb import EmbeddingFunction, Documents, Embeddings
from typing import List


def mean_pooling(model_output, attention_mask):
    """Mean pooling — усреднение токенов с учётом маски внимания."""
    token_embeddings = model_output.last_hidden_state
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(
        input_mask_expanded.sum(1), min=1e-9
    )


class PplxEmbedFunction(EmbeddingFunction):
    """Кодирование запросов — стандартная модель (короткие тексты, можно на MPS)."""

    def __init__(self, model_name: str = "perplexity-ai/pplx-embed-v1-0.6b"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name, trust_remote_code=True)
        self.model.eval()

        if torch.cuda.is_available():
            self.device = torch.device("cuda")
        elif torch.backends.mps.is_available():
            self.device = torch.device("mps")
        else:
            self.device = torch.device("cpu")

        self.model.to(self.device)

    def __call__(self, input: Documents) -> Embeddings:
        inputs = self.tokenizer(
            input, padding=True, truncation=True, return_tensors="pt"
        ).to(self.device)

        with torch.no_grad():
            model_output = self.model(**inputs)

        embeddings = mean_pooling(model_output, inputs["attention_mask"])
        embeddings = F.normalize(embeddings, p=2, dim=-1)
        return embeddings.cpu().tolist()


class PplxContextEmbedFunction(EmbeddingFunction):
    """Кодирование чанков с контекстом — контекстная модель.
    Работает на CPU, т.к. контекст + чанк = длинный текст, не влезает в MPS.
    """

    CONTEXT_SEPARATOR = "\n\n---\n\n"
    MAX_CONTEXT_CHARS = 8000  # Ограничиваем длину контекста документа

    def __init__(self, model_name: str = "perplexity-ai/pplx-embed-context-v1-0.6b"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(
            model_name, trust_remote_code=True, torch_dtype=torch.float32
        )
        self.model.eval()
        # Принудительно CPU для длинных контекстных входов
        self.device = torch.device("cpu")
        self.model.to(self.device)

    def __call__(self, input: Documents) -> Embeddings:
        inputs = self.tokenizer(
            input, padding=True, truncation=True, return_tensors="pt"
        ).to(self.device)

        with torch.no_grad():
            model_output = self.model(**inputs)

        embeddings = mean_pooling(model_output, inputs["attention_mask"])
        embeddings = F.normalize(embeddings, p=2, dim=-1)
        return embeddings.cpu().tolist()

    def _truncate_context(self, full_document: str) -> str:
        """Обрезаем документ до MAX_CONTEXT_CHARS чтобы не переполнить память."""
        if len(full_document) <= self.MAX_CONTEXT_CHARS:
            return full_document
        return full_document[:self.MAX_CONTEXT_CHARS] + "\n...[truncated]"

    def embed_with_context(self, chunks: List[str], full_document: str) -> Embeddings:
        """Получить эмбеддинги чанков с контекстом. Обработка по одному."""
        truncated_doc = self._truncate_context(full_document)
        all_embeddings = []

        for chunk in chunks:
            contextual_input = truncated_doc + self.CONTEXT_SEPARATOR + chunk

            inputs = self.tokenizer(
                [contextual_input], padding=True, truncation=True, return_tensors="pt"
            ).to(self.device)

            with torch.no_grad():
                model_output = self.model(**inputs)

            emb = mean_pooling(model_output, inputs["attention_mask"])
            emb = F.normalize(emb, p=2, dim=-1)
            all_embeddings.append(emb.squeeze(0))

            # Очищаем память после каждого чанка
            del inputs, model_output, emb
            torch.mps.empty_cache() if torch.backends.mps.is_available() else None

        stacked = torch.stack(all_embeddings)
        return stacked.tolist()