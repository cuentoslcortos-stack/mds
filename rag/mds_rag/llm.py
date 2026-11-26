# -*- coding: utf-8 -*-
"""Cliente de generación: Ollama local (default) u OpenRouter (opcional, :free).

Por defecto todo corre en la máquina del usuario: 0 tokens, 0 costo, offline.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Iterator

from . import config
from .embeddings import modelos_disponibles

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) mds-rag/1.0"
_CATALOGO: dict = {"datos": None, "momento": 0.0}


class ErrorLLM(RuntimeError):
    pass


# --- TRABA DE COSTO ---------------------------------------------------------
def catalogo_openrouter() -> dict:
    """Catalogo de modelos de OpenRouter (cacheado 5 minutos)."""
    ahora = time.monotonic()
    if _CATALOGO["datos"] is not None and ahora - _CATALOGO["momento"] < 300:
        return _CATALOGO["datos"]
    key = config.openrouter_key()
    if not key:
        return {}
    req = urllib.request.Request(
        config.OPENROUTER_MODELS_URL,
        headers={"Authorization": f"Bearer {key}", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            datos = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {}
    catalogo = {m["id"]: m for m in datos.get("data", []) if "id" in m}
    _CATALOGO["datos"] = catalogo
    _CATALOGO["momento"] = ahora
    return catalogo


def modelo_es_gratis(modelo: str) -> bool:
    """True solo si el modelo es ':free' Y su precio es 0/0.

    Con esto el motor no puede cobrar un centavo ni aunque la cuenta tenga
    saldo: los ':free' de OpenRouter usan la cuota gratuita y, agotada,
    devuelven 429 (nunca cobran del saldo).
    """
    if not modelo:
        return False
    if not modelo.endswith(":free"):
        return False
    info = catalogo_openrouter().get(modelo)
    if info is None:
        # Sin catalogo no se puede verificar: por seguridad, no se usa.
        return False
    precio = info.get("pricing", {})
    try:
        return float(precio.get("prompt", 1) or 0) == 0 and float(
            precio.get("completion", 1) or 0
        ) == 0
    except (TypeError, ValueError):
        return False


def exigir_gratis(modelo: str) -> None:
    if not config.SOLO_GRATIS:
        return
    if not modelo_es_gratis(modelo):
        raise ErrorLLM(
            f"El modelo '{modelo}' no es un modelo gratuito verificado "
            f"(':free' con precio 0/0). Con MDS_SOLO_GRATIS=1 el motor no llama "
            f"a modelos que puedan tener costo. Usá uno de la lista de "
            f"gratuitos o poné MDS_SOLO_GRATIS=0 si querés habilitar los pagos."
        )


def modelos_gratis() -> list[dict]:
    """Modelos :free verificados (para mostrarlos en la interfaz)."""
    resultado = []
    for mid, info in catalogo_openrouter().items():
        if not mid.endswith(":free"):
            continue
        precio = info.get("pricing", {})
        try:
            if float(precio.get("prompt", 1) or 0) != 0 or float(
                precio.get("completion", 1) or 0
            ) != 0:
                continue
        except (TypeError, ValueError):
            continue
        resultado.append(
            {
                "id": mid,
                "nombre": info.get("name", mid),
                "contexto": info.get("context_length", 0),
            }
        )
    return sorted(resultado, key=lambda m: -m["contexto"])


def resolver_modelo(candidato: str | None = None) -> str:
    """Devuelve un tag de modelo que Ollama realmente tenga instalado.

    Ollama resuelve 'qwen2.5' a 'qwen2.5:latest' pero NO 'qwen2.5:7b' si
    ese tag no existe. Este resolver evita el 404 "model not found".
    """
    pedido = candidato or config.LLM_MODEL
    disponibles = modelos_disponibles()
    if not disponibles:
        return pedido
    if pedido in disponibles:
        return pedido

    base_pedido = pedido.split(":")[0]
    for d in disponibles:
        if d == base_pedido or d.split(":")[0] == base_pedido:
            return d
    for alterno in config.LLM_FALLBACKS:
        if alterno in disponibles:
            return alterno
        base = alterno.split(":")[0]
        for d in disponibles:
            if d.split(":")[0] == base:
                return d
    return disponibles[0]


def _post_json(url: str, payload: dict, headers: dict | None = None, timeout: int = 900) -> dict:
    datos = json.dumps(payload).encode("utf-8")
    cabeceras = {"Content-Type": "application/json"}
    if headers:
        cabeceras.update(headers)
    req = urllib.request.Request(url, data=datos, headers=cabeceras)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detalle = exc.read().decode("utf-8", "replace")[:500]
        raise ErrorLLM(f"{exc.code}: {detalle}") from exc
    except urllib.error.URLError as exc:
        raise ErrorLLM(f"No se pudo conectar: {exc.reason}") from exc


def _post_stream(url: str, payload: dict, headers: dict | None = None, timeout: int = 900) -> Iterator[str]:
    datos = json.dumps(payload).encode("utf-8")
    cabeceras = {"Content-Type": "application/json"}
    if headers:
        cabeceras.update(headers)
    req = urllib.request.Request(url, data=datos, headers=cabeceras)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as exc:
        detalle = exc.read().decode("utf-8", "replace")[:500]
        raise ErrorLLM(f"{exc.code}: {detalle}") from exc
    except urllib.error.URLError as exc:
        raise ErrorLLM(f"No se pudo conectar: {exc.reason}") from exc

    with resp:
        for raw in resp:
            linea = raw.decode("utf-8", "replace").strip()
            if not linea:
                continue
            if linea.startswith("data:"):
                linea = linea[5:].strip()
            if linea == "[DONE]":
                break
            try:
                yield linea
            except Exception:  # pragma: no cover -Stream corruptos
                continue


def _payload_ollama(mensajes: list[dict], modelo: str, stream: bool) -> dict:
    return {
        "model": modelo,
        "messages": mensajes,
        "stream": stream,
        "options": {
            "temperature": config.TEMPERATURA,
            "num_ctx": config.NUM_CTX,
        },
    }


def chat(
    mensajes: list[dict],
    modelo: str | None = None,
    backend: str | None = None,
    temperatura: float | None = None,
) -> dict:
    """Genera una respuesta completa (sin streaming)."""
    backend = backend or config.LLM_BACKEND
    if backend == "openrouter":
        return _chat_openrouter(mensajes, modelo or config.LLM_MODEL_B_NUBE, temperatura)
    modelo = resolver_modelo(modelo)
    payload = _payload_ollama(mensajes, modelo, False)
    if temperatura is not None:
        payload["options"]["temperature"] = temperatura
    data = _post_json(config.OLLAMA_HOST + "/api/chat", payload)
    return {
        "texto": data.get("message", {}).get("content", ""),
        "modelo": data.get("model", modelo),
        "backend": "ollama",
    }


def chat_stream(
    mensajes: list[dict],
    modelo: str | None = None,
    backend: str | None = None,
    temperatura: float | None = None,
) -> Iterator[str]:
    """Genera la respuesta token a token."""
    backend = backend or config.LLM_BACKEND
    if backend == "openrouter":
        yield from _chat_stream_openrouter(
            mensajes, modelo or config.LLM_MODEL_B_NUBE, temperatura
        )
        return
    modelo = resolver_modelo(modelo)
    payload = _payload_ollama(mensajes, modelo, True)
    if temperatura is not None:
        payload["options"]["temperature"] = temperatura
    for linea in _post_stream(config.OLLAMA_HOST + "/api/chat", payload):
        try:
            obj = json.loads(linea)
        except json.JSONDecodeError:
            continue
        if obj.get("done"):
            break
        delta = obj.get("message", {}).get("content", "")
        if delta:
            yield delta


def _chat_openrouter(mensajes: list[dict], modelo: str, temperatura: float | None) -> dict:
    key = config.openrouter_key()
    if not key:
        raise ErrorLLM(
            "No se encontro la key de OpenRouter. Exporta OPENROUTER_API_KEY "
            "o apunta MDS_OPENROUTER_KEY_FILE al archivo que la tiene."
        )
    exigir_gratis(modelo)
    payload = {
        "model": modelo,
        "messages": mensajes,
        "temperature": config.TEMPERATURA if temperatura is None else temperatura,
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "HTTP-Referer": "http://127.0.0.1:8765",
        "X-Title": "Sistema MDS",
        "User-Agent": USER_AGENT,
    }
    data = _post_json(config.OPENROUTER_URL, payload, headers)
    texto = ""
    if data.get("choices"):
        texto = data["choices"][0].get("message", {}).get("content", "")
    return {"texto": texto, "modelo": modelo, "backend": "openrouter"}


def _chat_stream_openrouter(
    mensajes: list[dict], modelo: str, temperatura: float | None
) -> Iterator[str]:
    key = config.openrouter_key()
    if not key:
        raise ErrorLLM(
            "No se encontro la key de OpenRouter. Exporta OPENROUTER_API_KEY "
            "o apunta MDS_OPENROUTER_KEY_FILE al archivo que la tiene."
        )
    exigir_gratis(modelo)
    payload = {
        "model": modelo,
        "messages": mensajes,
        "temperature": config.TEMPERATURA if temperatura is None else temperatura,
        "stream": True,
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "HTTP-Referer": "http://127.0.0.1:8765",
        "X-Title": "Sistema MDS",
        "User-Agent": USER_AGENT,
    }
    for linea in _post_stream(config.OPENROUTER_URL, payload, headers):
        try:
            obj = json.loads(linea)
        except json.JSONDecodeError:
            continue
        if not obj.get("choices"):
            continue
        delta = obj["choices"][0].get("delta", {}).get("content", "")
        if delta:
            yield delta
