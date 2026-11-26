# -*- coding: utf-8 -*-
"""Recuperación híbrida sobre el corpus: léxica (BM25) + vectorial + re-ranking.

Por qué híbrida: el embedding (aunque sea qwen3-embedding) esEnglish-centric y
en español técnico se le escapan términos literales como "represión" o
"Verneinung". El BM25 rescata esos casos y la fusión por RRF combina ambos.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict

import numpy as np

from . import config, embeddings
from .chunker import sin_acentos

STOPWORDS = {
    "the", "and", "for", "que", "los", "las", "del", "por", "con", "una", "uno",
    "sus", "como", "mas", "pero", "este", "esta", "esto", "es", "son", "fue",
    "ser", "todo", "toda", "todos", "todas", "hay", "sin", "sobre", "entre",
    "cuando", "donde", "cual", "cuales", "tambien", "asi", "ya", "se", "le",
    "les", "lo", "al", "a", "de", "y", "o", "u", "en", "un", "una", "el", "la",
    "no", "ni", "ni", "si", "me", "te", "se", "nos", "os", "por", "para", "con",
    "que", "del", "al", "lo", "le", "su", "sus", "muy", "mas", "poco", "otro",
    "otra", "otros", "otras", "mismo", "misma", "puede", "pueden", "hace",
    "hay", "sea", "ser", "sido", "estar", "tiene", "tienen", "cada", "ante",
    "tras", "esto", "esta", "aqui", "ahi", "tambien", "bien", "vez", "solo",
}

TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenizar(texto: str) -> list[str]:
    limpio = sin_acentos(texto.lower())
    return [
        t
        for t in TOKEN_RE.findall(limpio)
        if len(t) > 2 and t not in STOPWORDS and not t.isdigit()
    ]


class BM25:
    """BM25 clásico con postings invertidos (rápido en Python puro)."""

    def __init__(self, corpus: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.n = len(corpus)
        self.largo = np.array([len(d) for d in corpus], dtype=np.float32)
        self.promedio = float(self.largo.mean()) if self.n else 1.0
        self.postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        for i, toks in enumerate(corpus):
            for termino, freq in Counter(toks).items():
                self.postings[termino].append((i, freq))
        self.idf: dict[str, float] = {}
        for termino, postings in self.postings.items():
            df = len(postings)
            self.idf[termino] = math.log(1 + (self.n - df + 0.5) / (df + 0.5))

    def puntuar(self, consulta: list[str]) -> np.ndarray:
        scores = np.zeros(self.n, dtype=np.float32)
        for termino in set(consulta):
            idf = self.idf.get(termino)
            if idf is None:
                continue
            for i, freq in self.postings[termino]:
                denom = freq + self.k1 * (
                    1 - self.b + self.b * self.largo[i] / self.promedio
                )
                scores[i] += idf * freq * (self.k1 + 1) / denom
        return scores


def _norm(valores: np.ndarray) -> np.ndarray:
    if valores.size == 0:
        return valores
    maximo = float(valores.max())
    if maximo <= 0:
        return np.zeros_like(valores)
    return valores / maximo


def _rrf(rankings: list[list[int]], pesos: list[float], k: int = 60) -> np.ndarray:
    """Reciprocal Rank Fusion: combina rankings sin depender de escalas."""
    total = np.zeros(max((max(r) + 1 for r in rankings if r), default=1), dtype=np.float32)
    for ranking, peso in zip(rankings, pesos):
        for posicion, idx in enumerate(ranking):
            total[idx] += peso / (k + posicion + 1)
    return total


class Recuperador:
    def __init__(self, store) -> None:
        self.store = store
        self.bm25 = BM25(
            [
                tokenizar(f"{f.titulo} {f.texto}")
                for f in store.fragmentos
            ]
        )
        self.vectores = store.vectores  # ya normalizados

    # --- consulta ------------------------------------------------------------
    def buscar(
        self,
        consulta: str,
        k: int | None = None,
        candidatos: int | None = None,
    ) -> list[dict]:
        if not self.store.fragmentos:
            return []
        k = k or config.TOP_K
        candidatos = candidatos or config.CANDIDATOS

        toks = tokenizar(consulta)
        scores_lexico = self.bm25.puntuar(toks)

        vec_consulta = embeddings.embed_textos(
            [consulta], modelo=self.store.modelo, prefijo=embeddings.PREFIJO_CONSULTA
        )
        if vec_consulta.size == 0:
            scores_vector = np.zeros(len(self.store.fragmentos), dtype=np.float32)
        else:
            q = embeddings.normalizar(vec_consulta)[0]
            scores_vector = self.vectores @ q

        ranking_lex = list(np.argsort(-scores_lexico)[:candidatos])
        ranking_vec = list(np.argsort(-scores_vector)[:candidatos])

        fusion = _rrf([ranking_lex, ranking_vec], [config.PESO_LEXICO, config.PESO_VECTOR])
        fusion = _norm(fusion)

        orden = list(np.argsort(-fusion)[:candidatos])
        lexical_norm = _norm(scores_lexico)

        resultados = []
        for idx in orden:
            frag = self.store.fragmentos[int(idx)]
            resultados.append(
                {
                    "id": frag.id,
                    "archivo": frag.archivo,
                    "documento": frag.documento,
                    "capitulo": frag.capitulo,
                    "seccion": frag.seccion,
                    "titulo": frag.titulo,
                    "texto": frag.texto,
                    "palabras": frag.palabras,
                    "score": round(float(fusion[idx]), 4),
                    "score_vector": round(float(scores_vector[idx]), 4),
                    "score_lexico": round(float(lexical_norm[idx]), 4),
                }
            )
        return resultados[:k]

    def para_embedding(self, resultados: list[dict]) -> str:
        """Contexto en texto, listo para mandarle al modelo de lenguaje."""
        bloques = []
        for i, r in enumerate(resultados, start=1):
            ubicacion = r["capitulo"]
            if r["seccion"]:
                ubicacion = f"{ubicacion} > {r['seccion']}" if ubicacion else r["seccion"]
            bloques.append(
                f"[{i}] FUENTE: {r['documento']}\n"
                f"    UBICACIÓN: {ubicacion}\n"
                f"    TEXTO:\n{r['texto']}"
            )
        return "\n\n".join(bloques)
