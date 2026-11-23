import math
import re

import httpx

from .config import settings
from .models import DocumentChunk


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def retrieve_chunks(chunks: list[DocumentChunk], query: str, limit: int) -> list[tuple[DocumentChunk, float]]:
    query_terms = set(tokenize(query))
    scored: list[tuple[DocumentChunk, float]] = []

    for chunk in chunks:
        terms = tokenize(chunk.content)
        if not terms:
            continue
        frequencies = {term: terms.count(term) for term in query_terms if term in terms}
        if not frequencies:
            score = 0.0
        else:
            score = sum((1.0 + math.log(count)) * (1.0 / math.sqrt(len(terms))) for count in frequencies.values())
        if score > 0:
            scored.append((chunk, score))

    scored.sort(key=lambda item: item[1], reverse=True)
    candidates = scored[: max(limit * 4, limit)]
    return rerank(query, candidates)[:limit]


def rerank(query: str, candidates: list[tuple[DocumentChunk, float]]) -> list[tuple[DocumentChunk, float]]:
    if not settings.cohere_api_key:
        return candidates

    try:
        response = httpx.post(
            "https://api.cohere.com/v2/rerank",
            headers={"Authorization": f"Bearer {settings.cohere_api_key}"},
            json={
                "model": "rerank-v3.5",
                "query": query,
                "documents": [chunk.content for chunk, _ in candidates],
                "top_n": len(candidates),
            },
            timeout=30,
        )
        response.raise_for_status()
        ranking = response.json()["results"]
        return [(candidates[item["index"]][0], float(item["relevance_score"])) for item in ranking]
    except (httpx.HTTPError, KeyError, ValueError, IndexError):
        return candidates


def grounded_answer(query: str, results: list[tuple[DocumentChunk, float]]) -> str:
    if not results:
        return "I could not find relevant information in the documents available to your organization."

    if settings.openai_api_key:
        context = "\n\n".join(
            f"[Document {index + 1}: {chunk.document.filename}]\\n{chunk.content}"
            for index, (chunk, _) in enumerate(results)
        )
        try:
            response = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={
                    "model": settings.openai_model,
                    "temperature": 0,
                    "messages": [
                        {"role": "system", "content": "Answer only from the supplied context. If unsupported, say that it is not stated. Cite sources using [n]."},
                        {"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{query}"},
                    ],
                },
                timeout=60,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            if content:
                return content
        except (httpx.HTTPError, KeyError, ValueError, IndexError):
            pass

    sentences: list[str] = []
    query_terms = set(tokenize(query))
    for chunk, _ in results:
        for sentence in re.split(r"(?<=[.!?])\s+", chunk.content):
            sentence = sentence.strip()
            if sentence and query_terms.intersection(set(tokenize(sentence))):
                sentences.append(sentence)
            if len(sentences) >= 5:
                break
        if len(sentences) >= 5:
            break
    return " ".join(sentences) if sentences else results[0][0].content[:1200]
