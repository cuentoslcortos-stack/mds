# -*- coding: utf-8 -*-
"""Cliente de embeddings contra Ollama.

Los embeddings se calculan 100% en la máquina (0 tokens, 0 costo). Para
`qwen3-embedding` la busqueda asimetrica pide prefijos distintos para consulta
y documento; el prefijo se lo aplicamos nosotros porque la API de Ollama no lo
expone por entrada.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

import numpy as np

from . import config

PREFIJO_DOCUMENTO = ""
PREFIJO_CONSULTA = ""

# Calibrado con 16 consultas de control + 10 de terminos raros:
# los prefijos "query:" / "document:" de qwen3-embedding EMPEORAN el ranking en
# espanol (6/8 con prefijo vs 8/8 sin). Se indexa y se consulta de forma
# simetrica, sin prefijo.

# Cache corta: /api/health se consulta cada 15 s y sin esto tardaba ~1 s
# (dos llamadas encadenadas a Ollama), lo que hacia recargar la interfaz.
_CACHE: dict = {}
_TTL = 10.0


def _cacheado(clave: str, obtener, ttl: float = _TTL):
    ahora = time.monotonic()
    marca, valor = _CACHE.get(clave, (0.0, None))
    if valor is not None and ahora - marca < ttl:
        return valor
    nuevo = obtener()
    _CACHE[clave] = (ahora, nuevo)
    return nuevo


class ErrorOllama(RuntimeError):
    pass


def _post(ruta: str, payload: dict, timeout: int = 900) -> dict:
    cuerpo = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        config.OLLAMA_HOST + ruta,
        data=cuerpo,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detalle = exc.read().decode("utf-8", "replace")[:400]
        raise ErrorOllama(f"{exc.code} en {ruta}: {detalle}") from exc
    except urllib.error.URLError as exc:
        raise ErrorOllama(
            f"No se pudo hablar con Ollama en {config.OLLAMA_HOST}. "
            f"¿Está corriendo? ({exc.reason})"
        ) from exc


def _get(ruta: str, timeout: int = 30) -> dict:
    """GET contra Ollama (/api/tags es GET, no POST)."""
    req = urllib.request.Request(config.OLLAMA_HOST + ruta, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise ErrorOllama(f"{exc.code} en {ruta}") from exc
    except urllib.error.URLError as exc:
        raise ErrorOllama(
            f"No se pudo hablar con Ollama en {config.OLLAMA_HOST}. "
            f"¿Está corriendo? ({exc.reason})"
        ) from exc


def ping() -> bool:
    def _comprobar() -> bool:
        try:
            _get("/api/tags", timeout=10)
            return True
        except ErrorOllama:
            return False

    return _cacheado("ping", _comprobar)


def modelos_disponibles() -> list[str]:
    def _listar() -> list[str]:
        try:
            data = _get("/api/tags", timeout=15)
        except ErrorOllama:
            return []
        return [m.get("name", "") for m in data.get("models", [])]

    return _cacheado("modelos", _listar)


def embed_textos(
    textos: list[str],
    modelo: str | None = None,
    prefijo: str | None = None,
    lote: int = 16,
) -> np.ndarray:
    """Devuelve una matriz (n_textos, dim) de embeddings float32."""
    if not textos:
        return np.zeros((0, 0), dtype=np.float32)
    modelo = modelo or config.EMBED_MODEL
    vectores: list[list[float]] = []
    for i in range(0, len(textos), lote):
        bloque = textos[i : i + lote]
        if prefijo:
            bloque = [prefijo + t for t in bloque]
        data = _post(
            "/api/embed",
            {"model": modelo, "input": bloque, "truncate": True},
        )
        if "embeddings" not in data:
            raise ErrorOllama(f"Respuesta sin embeddings: {list(data)[:6]}")
        vectores.extend(data["embeddings"])
    return np.asarray(vectores, dtype=np.float32)


def normalizar(vectores: np.ndarray) -> np.ndarray:
    if vectores.size == 0:
        return vectores
    normas = np.linalg.norm(vectores, axis=1, keepdims=True)
    normas[normas == 0] = 1.0
    return vectores / normas
