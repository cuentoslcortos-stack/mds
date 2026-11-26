# -*- coding: utf-8 -*-
"""Configuración central del motor RAG del Sistema MDS.

Todo es local por defecto: embeddings y generación contra Ollama en 127.0.0.1.
Nada sale a la red salvo que se elija explícitamente el backend 'openrouter'.
"""
from __future__ import annotations

import os
from pathlib import Path

# Sistema/mds_rag/config.py -> Sistema/
RAIZ = Path(__file__).resolve().parent.parent.parent

BASE_DIR = Path(os.environ.get("MDS_BASE_DIR", str(RAIZ / "base-conocimiento")))
STORAGE_DIR = Path(os.environ.get("MDS_RAG_STORAGE", str(RAIZ / "rag" / "storage")))
SKILL_PATH = Path(os.environ.get("MDS_SKILL", str(RAIZ / "SKILL.md")))
WEB_DIST = Path(os.environ.get("MDS_WEB_DIST", str(RAIZ / "web" / "dist")))

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
EMBED_MODEL = os.environ.get("MDS_EMBED_MODEL", "qwen3-embedding:0.6b")
LLM_MODEL = os.environ.get("MDS_LLM_MODEL", "qwen2.5:latest")
# El informe MDS (modo B) exige mas rigor que una consulta rapida. Medido con
# el caso real (42 anos, diferencia de edad), qwen3:30b-a3b (18 GB, MoE con
# 3.3B activos) gana claramente a gemma3:12b: la pregunta de 4.3 sale anclada
# en el significante nodal y la 4.1 lee el plus-de-gozar de la "orden".
# Cuesta ~5,7 min (gemma3:12b: ~6,4 min), asi que entra de sobra en el
# presupuesto de 20 min por informe.
LLM_MODEL_B = os.environ.get("MDS_LLM_MODEL_B", "qwen3:30b-a3b")
LLM_BACKEND = os.environ.get("MDS_LLM_BACKEND", "ollama")  # ollama | openrouter
# Modo B: nube (gratis) con reintento al modelo local, o solo local.
#   auto  -> intenta la nube y, si falla (cuota agotada, sin red), cae al local
#   nube  -> solo nube
#   local -> solo local: nada sale de la maquina
# Por defecto 'auto': ERNIE 5.5 Flash (chino, gratis) tarda 1,3 min y fundamenta
# en las 16 fuentes, contra 6-13 min del modelo local. En la barra de la
# interfaz se puede volver a 'local' con un clic.
MODO_B_NUBE = os.environ.get("MDS_MODO_B_NUBE", "auto").lower()
# ERNIE 5.5 Flash (Baidu) en la cuota gratuita de OpenRouter: verificado con
# precio 0/0. Medido con el caso real: 17.836 chars en 1,3 min fundamentando
# las 16 fuentes, contra 6,3 min del qwen3:30b-a3b local. Costo: 0.
#   (en la cuota :free solo hay dos chinos: este y inclusionai/ling-3.2-flash)
LLM_MODEL_B_NUBE = os.environ.get(
    "MDS_LLM_MODEL_B_NUBE", "baidu/ernie-5.5-flash-preview:free"
)
# Traba de costo: con esto en 1 el motor se NIEGA a llamar a un modelo de
# OpenRouter que no sea ':free' con precio 0/0, aun si la cuenta tiene saldo.
SOLO_GRATIS = os.environ.get("MDS_SOLO_GRATIS", "1") == "1"
# De donde sacar la key de OpenRouter (sin escribirla en ningun lado).
OPENROUTER_KEY_FILES = [
    os.environ.get("MDS_OPENROUTER_KEY_FILE", ""),
    r"C:\Users\alanv\Apps\FreeLLMAPI\freellmapi.config.json",
]
# Si el modelo configurado no esta instalado, se cae a esta lista.
LLM_FALLBACKS = [
    "gemma3:12b",
    "qwen3:30b-a3b",
    "qwen2.5:latest",
    "qwen3-vl:8b-instruct",
]
# El prompt del modo B (SKILL + fragmentos + datos lexicos + mapa) ronda los
# 20k tokens con 16 fragmentos: con 16384 la ventana queda al limite de
# truncamiento. 32768 deja margen y qwen3:30b-a3b lo soporta de sobra.
NUM_CTX = int(os.environ.get("MDS_NUM_CTX", "32768"))
TEMPERATURA = float(os.environ.get("MDS_TEMPERATURA", "0.3"))

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.environ.get(
    "MDS_OPENROUTER_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free"
)

# --- Parámetros de troceado y recuperación -----------------------------------
MAX_WORDS = int(os.environ.get("MDS_CHUNK_WORDS", "320"))
MIN_WORDS = int(os.environ.get("MDS_CHUNK_MIN_WORDS", "45"))
# En Modo B se recuperan mas fragmentos que en modo A: el informe tiene que
# fundamentarse en TODO el corpus recuperado, no en 4 fuentes. Con 16
# fragmentos el prompt ronda los 20k tokens (NUM_CTX 32768).
TOP_K = int(os.environ.get("MDS_TOP_K", "4"))
TOP_K_B = int(os.environ.get("MDS_TOP_K_B", "16"))
CANDIDATOS = int(os.environ.get("MDS_CANDIDATOS", "20"))
PESO_VECTOR = float(os.environ.get("MDS_PESO_VECTOR", "0.85"))
PESO_LEXICO = float(os.environ.get("MDS_PESO_LEXICO", "0.15"))
PESO_RERANK = float(os.environ.get("MDS_PESO_RERANK", "0.5"))

# --- Servidor ---------------------------------------------------------------
HOST = os.environ.get("MDS_RAG_HOST", "127.0.0.1")
PUERTO = int(os.environ.get("MDS_RAG_PORT", "8765"))

ORIGENES_PERMITIDOS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]


def openrouter_key() -> str:
    """Devuelve la key de OpenRouter.

    Orden: variable de entorno OPENROUTER_API_KEY, archivo indicado por
    MDS_OPENROUTER_KEY_FILE, y los archivos conocidos. No se escribe la key
    en ningun lado del proyecto.
    """
    if OPENROUTER_KEY:
        return OPENROUTER_KEY
    import re

    patron = re.compile(r"sk-or-v1-[A-Za-z0-9_\-]{10,}")
    for ruta in OPENROUTER_KEY_FILES:
        if not ruta:
            continue
        try:
            crudo = Path(ruta).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        encontrado = patron.search(crudo)
        if encontrado:
            return encontrado.group(0)
    return ""
