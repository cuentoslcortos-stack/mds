# -*- coding: utf-8 -*-
"""Servidor HTTP local del motor RAG.

Usa solo la biblioteca estandar: no hace falta instalar FastAPI ni nada.
Expone la API que consume la web app y, si existe `web/dist`, sirve la
interfaz compilada en el mismo puerto.
"""
from __future__ import annotations

import json
import mimetypes
import re
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from . import (
    config,
    corrector_transcripcion,
    embeddings,
    llm,
    mapa_fragmentos,
    prompt,
    verificador_citas,
)
from .retrieval import Recuperador
from .store import Store

_ESTADO: dict = {"store": None, "recuperador": None}

# Los doce apartados que el protocolo MDS obliga a tener. Si al modelo se le
# salta alguno (le pasa: a veces arranca por la Fase 2), el sistema lo detecta
# y reintenta: un informe sin el nucleo del malestar no es un informe.
APARTADOS = [
    "1.1", "1.2", "1.3",
    "2.1", "2.2", "2.3",
    "3.1", "3.2", "3.3",
    "4.1", "4.2", "4.3",
]


def _apartados_faltantes(texto: str) -> list[str]:
    faltan = []
    for ap in APARTADOS:
        patron = r"\*+\s*" + re.escape(ap) + r"\b"
        if not re.search(patron, texto):
            faltan.append(ap)
    return faltan


def obtener_estado():
    if _ESTADO["store"] is None:
        store = Store()
        _ESTADO["store"] = store
        _ESTADO["recuperador"] = Recuperador(store) if store.listo else None
    return _ESTADO["store"], _ESTADO["recuperador"]


def _reconstruir() -> None:
    store = _ESTADO["store"]
    _ESTADO["recuperador"] = Recuperador(store) if store.listo else None


def _fuentes(resultados: list[dict]) -> list[dict]:
    return [
        {
            "id": r["id"],
            "archivo": r["archivo"],
            "documento": r["documento"],
            "capitulo": r["capitulo"],
            "seccion": r["seccion"],
            "titulo": r["titulo"],
            "score": r["score"],
            "score_vector": r.get("score_vector", 0.0),
            "score_lexico": r.get("score_lexico", 0.0),
            "extracto": r["texto"],
            "palabras": r["palabras"],
        }
        for r in resultados
    ]


class Handler(BaseHTTPRequestHandler):
    server_version = "MDS-RAG/1.0"
    protocol_version = "HTTP/1.1"

    # --- utilidades ----------------------------------------------------------
    def _cors(self) -> None:
        origen = self.headers.get("Origin")
        if origen and origen in config.ORIGENES_PERMITIDOS:
            self.send_header("Access-Control-Allow-Origin", origen)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, obj: dict, status: int = 200) -> None:
        cuerpo = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self._cors()
            self.end_headers()
            self.wfile.write(cuerpo)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            # El cliente se fue (cerró la pestaña, abortó la petición): no es
            # un error del servidor, no hay a quién avisarle.
            pass

    def _error(self, mensaje: str, status: int = 500) -> None:
        self._json({"error": mensaje}, status)

    def _leer_json(self) -> dict:
        largo = int(self.headers.get("Content-Length") or 0)
        if largo <= 0:
            return {}
        crudo = self.rfile.read(largo)
        try:
            return json.loads(crudo.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    def _ndjson(self, generador) -> None:
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Accel-Buffering", "no")
            self._cors()
            self.end_headers()
            for obj in generador:
                self.wfile.write((json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8"))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass

    def log_message(self, fmt: str, *args) -> None:
        print(f"[{time.strftime('%H:%M:%S')}] {self.address_string()} {fmt % args}", flush=True)

    # --- verbos --------------------------------------------------------------
    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        ruta = urlparse(self.path).path
        try:
            if ruta == "/api/health":
                return self._health()
            if ruta == "/api/documentos":
                store, _ = obtener_estado()
                return self._json({"documentos": store.documentos()})
            if ruta == "/api/modelos":
                return self._json(self._modelos())
            if ruta.startswith("/api/"):
                return self._error("Endpoint desconocido", 404)
            return self._estatico(ruta)
        except Exception as exc:  # pragma: no cover
            traceback.print_exc()
            return self._error(str(exc), 500)

    def do_POST(self) -> None:  # noqa: N802
        ruta = urlparse(self.path).path
        body = self._leer_json()
        try:
            if ruta == "/api/buscar":
                return self._buscar(body)
            if ruta == "/api/chat":
                return self._chat(body)
            if ruta == "/api/reindex":
                return self._reindex(body)
            if ruta == "/api/motor":
                return self._motor(body)
            return self._error("Endpoint desconocido", 404)
        except Exception as exc:  # pragma: no cover
            traceback.print_exc()
            return self._error(str(exc), 500)

    # --- handlers ------------------------------------------------------------
    def _health(self) -> None:
        store, _ = obtener_estado()
        modelos = embeddings.modelos_disponibles()
        self._json(
            {
                "ok": bool(embeddings.ping()),
                "ollama": bool(embeddings.ping()),
                "embed_model": store.modelo,
                "embed_disponible": store.modelo in modelos,
                "llm_model": llm.resolver_modelo(config.LLM_MODEL),
                "llm_model_b": llm.resolver_modelo(config.LLM_MODEL_B),
                "llm_pedido": config.LLM_MODEL,
                "nube": {
                    "modelo": config.LLM_MODEL_B_NUBE,
                    "gratis_verificado": llm.modelo_es_gratis(config.LLM_MODEL_B_NUBE),
                    "politica": config.MODO_B_NUBE,
                    "solo_gratis": config.SOLO_GRATIS,
                    "key_encontrada": bool(config.openrouter_key()),
                },
                "backend": config.LLM_BACKEND,
                "modelos_disponibles": modelos,
                "indice": {
                    "chunks": len(store.fragmentos),
                    "documentos": len(store.documentos()),
                    "actualizado": store.actualizado,
                    "palabras": sum(f.palabras for f in store.fragmentos),
                },
            }
        )

    def _modelos(self) -> dict:
        """Modelos disponibles y con cuáles se puede trabajar sin costo."""
        return {
            "modo_a": {"modelo": config.LLM_MODEL, "backend": "ollama", "costo": 0},
            "modo_b": {
                "nube": {
                    "modelo": config.LLM_MODEL_B_NUBE,
                    "backend": "openrouter",
                    "costo": 0,
                    "verificado_gratis": llm.modelo_es_gratis(config.LLM_MODEL_B_NUBE),
                },
                "local": {"modelo": config.LLM_MODEL_B, "backend": "ollama", "costo": 0},
                "politica": config.MODO_B_NUBE,
            },
            "solo_gratis": config.SOLO_GRATIS,
            "gratuitos_disponibles": llm.modelos_gratis(),
        }

    def _buscar(self, body: dict) -> None:
        store, rec = obtener_estado()
        consulta = (body.get("consulta") or body.get("query") or "").strip()
        if not consulta:
            return self._error("Falta 'consulta'", 400)
        if rec is None:
            return self._error("El indice esta vacio. POST /api/reindex para construirlo.", 503)
        k = int(body.get("k") or config.TOP_K)
        resultados = rec.buscar(consulta, k=k)
        self._json({"consulta": consulta, "resultados": _fuentes(resultados)})

    def _chat(self, body: dict) -> None:
        store, rec = obtener_estado()
        if rec is None:
            return self._error("El indice esta vacio. POST /api/reindex para construirlo.", 503)

        pregunta = (body.get("pregunta") or body.get("consulta") or "").strip()
        modo = (body.get("modo") or "A").upper()
        transcripcion = body.get("transcripcion") or ""
        notas = body.get("notas") or ""
        informe = body.get("informe") or ""
        k = int(body.get("k") or (config.TOP_K_B if modo in ("B", "C") else config.TOP_K))
        historial = body.get("historial") or []
        stream = bool(body.get("stream", True))
        modelo = body.get("modelo") or None

        if modo == "B" and not transcripcion.strip():
            return self._error("El modo B (informe MDS) requiere 'transcripcion'", 400)
        if modo == "C" and not (informe.strip() and pregunta.strip()):
            return self._error(
                "El modo C (dialogo sobre el analisis) requiere 'informe' y 'pregunta'.",
                400,
            )

        # Correccion de transcripcion ANTES de todo: si el analista corrigio
        # una palabra, el modelo tiene que analizar la forma correcta. La
        # forma erronea no llega ni al prompt ni al indice.
        correcciones: list[dict] = []
        if transcripcion.strip():
            transcripcion, corr = corrector_transcripcion.corregir(transcripcion)
            correcciones += corr
        if notas.strip():
            _, corr = corrector_transcripcion.corregir(notas)
            for c in corr:
                transcripcion, hubo = corrector_transcripcion.aplicar(
                    transcripcion, c["erronea"], c["correcta"]
                )
                if hubo:
                    correcciones.append(c)

        # Cadena de motores. En modo B: nube gratuita primero y, si la cuota
        # se agota o no hay red, caida al modelo local. El modo A es siempre
        # local (responde en ~30 s).
        if modelo:
            # Si el modelo es un tag de Ollama va local; si es un id de
            # OpenRouter (tipo "baidu/ernie-5.5-flash-preview:free") va a la
            # nube. La guarda de costo igual lo revisa: solo :free con 0/0.
            disponibles = embeddings.modelos_disponibles()
            if not disponibles or modelo in disponibles:
                cadena = [("ollama", modelo)]
            else:
                cadena = [("openrouter", modelo)]
        elif modo in ("B", "C"):
            if config.MODO_B_NUBE == "nube":
                cadena = [("openrouter", config.LLM_MODEL_B_NUBE)]
            elif config.MODO_B_NUBE == "auto":
                cadena = [
                    ("openrouter", config.LLM_MODEL_B_NUBE),
                    ("ollama", config.LLM_MODEL_B),
                ]
            else:
                cadena = [("ollama", config.LLM_MODEL_B)]
        else:
            cadena = [("ollama", config.LLM_MODEL)]

        # En modo B la busqueda se guia por la pregunta MAS las notas del
        # analista MAS el propio discurso: asi funciona tambien cuando el
        # usuario pega todo junto en un solo campo (transcripcion con
        # correcciones pegadas dentro).
        consulta_busqueda = pregunta
        if modo == "B":
            consulta_busqueda = " ".join(
                p for p in (pregunta, notas, transcripcion) if p.strip()
            ).strip()
        elif modo == "C":
            # El informe es el contexto: la busqueda se guia por la pregunta
            # MAS lo que el informe ya establecio, para recuperar el material
            # que corresponde a lo que se esta preguntando.
            consulta_busqueda = " ".join(p for p in (pregunta, informe) if p.strip()).strip()

        resultados = rec.buscar(consulta_busqueda, k=k)
        contexto = rec.para_embedding(resultados)
        mensajes = prompt.construir_mensajes(
            pregunta,
            modo,
            transcripcion,
            contexto,
            historial,
            notas,
            resultados,
            correcciones,
            informe,
        )
        fuentes = _fuentes(resultados)

        if not stream:
            ultimo_error = None
            for backend, mod in cadena:
                try:
                    salida = llm.chat(mensajes, modelo=mod, backend=backend)
                    texto = salida["texto"]
                    faltan = _apartados_faltantes(texto)
                    intentos = 0
                    while modo == "B" and faltan and intentos < 1:
                        intentos += 1
                        aviso = (
                            "Tu informe anterior se salteo estos apartados: "
                            + ", ".join(faltan)
                            + ". Reescribi el informe COMPLETO desde el principio, "
                            "con los doce apartados en orden, empezando por "
                            "'Fase 1: La Escucha Activa'. No te saltes ninguno."
                        )
                        rehacer = mensajes + [{"role": "user", "content": aviso}]
                        salida = llm.chat(rehacer, modelo=mod, backend=backend)
                        texto = salida["texto"]
                        faltan = _apartados_faltantes(texto)
                    citas = {}
                    if modo == "B":
                        texto = mapa_fragmentos.completar_cotejo(texto, resultados)
                    if modo in ("B", "C"):
                        texto, citas = verificador_citas.verificar(texto, resultados)
                    return self._json(
                        {
                            "respuesta": texto,
                            "fuentes": fuentes,
                            "modelo": salida["modelo"],
                            "backend": salida["backend"],
                            "citas": citas,
                            "correcciones": correcciones,
                            "apartados_faltantes": faltan,
                            "reintentos": intentos,
                        }
                    )
                except Exception as exc:
                    ultimo_error = exc
                    if backend == "openrouter" and len(cadena) > 1:
                        continue
                    break
            return self._error(str(ultimo_error), 502)

        def generar():
            # Un evento por fuente: es el contrato que consume la web app.
            for fuente in fuentes:
                yield {"tipo": "fuente", "fuente": fuente}
            partes: list[str] = []
            usado = (cadena[-1][0], cadena[-1][1])
            for indice, (backend, mod) in enumerate(cadena):
                try:
                    for delta in llm.chat_stream(mensajes, modelo=mod, backend=backend):
                        partes.append(delta)
                        yield {"tipo": "delta", "texto": delta, "delta": delta}
                    usado = (backend, mod)
                    break
                except Exception as exc:  # pragma: no cover
                    traceback.print_exc()
                    if backend == "openrouter" and indice + 1 < len(cadena):
                        yield {
                            "tipo": "aviso",
                            "texto": (
                                f"El modelo gratuito en la nube no respondio ({exc}). "
                                f"Sigo con el modelo local ({cadena[indice + 1][1]})."
                            ),
                        }
                        partes = []
                        continue
                    yield {"tipo": "error", "error": str(exc)}
                    return
            texto = "".join(partes)
            citas = {}
            if modo == "B":
                texto = mapa_fragmentos.completar_cotejo(texto, resultados)
            if modo in ("B", "C"):
                texto, citas = verificador_citas.verificar(texto, resultados)
            faltan = _apartados_faltantes(texto) if modo == "B" else []
            if faltan:
                yield {
                    "tipo": "aviso",
                    "texto": (
                        "Al informe le faltan estos apartados: "
                        + ", ".join(faltan)
                        + ". Volvelo a pedir para que lo complete."
                    ),
                }
            yield {
                "tipo": "fin",
                "respuesta": texto,
                "citas": citas,
                "apartados_faltantes": faltan,
                "fuentes": fuentes,
                "modelo": usado[1] if usado[0] == "openrouter" else llm.resolver_modelo(usado[1]),
                "backend": usado[0],
            }

        self._ndjson(generar())

    def _motor(self, body: dict) -> None:
        """Cambia el motor del modo B en caliente (local / nube gratis).

        'local' -> nada sale de la maquina.
        'auto'  -> nube gratis primero, y si falla, el modelo local.
        'nube'  -> solo nube.
        """
        modo = str(body.get("modo") or "").strip().lower()
        if modo not in ("local", "auto", "nube"):
            return self._error("Modo invalido: se espera local, auto o nube.", 400)
        if modo != "local" and not config.openrouter_key():
            return self._error(
                "No se encontro la key de OpenRouter, asi que no hay modo nube. "
                "Segui en local.",
                400,
            )
        config.MODO_B_NUBE = modo
        return self._json(
            {
                "ok": True,
                "politica": config.MODO_B_NUBE,
                "modelo_nube": config.LLM_MODEL_B_NUBE,
                "modelo_local": config.LLM_MODEL_B,
            }
        )

    def _reindex(self, body: dict) -> None:
        store, _ = obtener_estado()
        t0 = time.time()
        resultado = store.indexar(forzar=bool(body.get("forzar")), verbose=False)
        _reconstruir()
        resultado["duracion_s"] = round(time.time() - t0, 2)
        resultado["palabras"] = sum(f.palabras for f in store.fragmentos)
        self._json(resultado)

    # --- estatico ------------------------------------------------------------
    def _estatico(self, ruta: str) -> None:
        raiz: Path = config.WEB_DIST
        if not raiz.exists():
            return self._json(
                {
                    "ok": True,
                    "mensaje": "Motor RAG activo. La interfaz web no esta compilada; "
                    "la API esta disponible en /api/*.",
                    "endpoints": [
                        "GET /api/health",
                        "GET /api/documentos",
                        "POST /api/buscar",
                        "POST /api/chat",
                        "POST /api/reindex",
                    ],
                }
            )

        limpio = unquote(urlparse(ruta).path).lstrip("/")
        destino = (raiz / limpio).resolve()
        if not str(destino).startswith(str(raiz.resolve())):
            return self._error("Ruta invalida", 403)
        if not destino.is_file():
            destino = raiz / "index.html"  # fallback SPA
        if not destino.is_file():
            return self._error("No encontrado", 404)

        tipo, _ = mimetypes.guess_type(str(destino))
        cuerpo = destino.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", tipo or "application/octet-stream")
        self.send_header("Content-Length", str(len(cuerpo)))
        self._cors()
        self.end_headers()
        self.wfile.write(cuerpo)


class Servidor(ThreadingHTTPServer):
    # allow_reuse_address = True (el default en Windows) deja que DOS procesos
    # bindeen el mismo puerto y el kernel reparte las conexiones: se termina
    # sirviendo una version vieja del codigo sin avisar. Con False, la segunda
    # instancia falla visible con "Address already in use".
    allow_reuse_address = False
    daemon_threads = True


def servir(host: str | None = None, puerto: int | None = None) -> None:
    host = host or config.HOST
    puerto = puerto or config.PUERTO
    obtener_estado()
    try:
        httpd = Servidor((host, puerto), Handler)
    except OSError as exc:
        raise SystemExit(
            f"No se pudo abrir el puerto {puerto}: {exc}\n"
            f"Seguramente ya hay un motor RAG corriendo. "
            f"Buscalo con: Get-NetTCPConnection -LocalPort {puerto}"
        ) from exc
    print(f"Motor RAG MDS escuchando en http://{host}:{puerto}")
    print(f"  Corpus:   {config.BASE_DIR}")
    print(
        f"  Embedding:{config.EMBED_MODEL}\n"
        f"  Modo A: {config.LLM_MODEL} (local)\n"
        f"  Modo B: {config.LLM_MODEL_B_NUBE} (nube gratis) "
        f"-> {config.LLM_MODEL_B} (local, de respaldo)\n"
        f"  Politica de costo: solo gratis = {config.SOLO_GRATIS}"
    )
    print("  Ctrl+C para salir.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        httpd.server_close()
