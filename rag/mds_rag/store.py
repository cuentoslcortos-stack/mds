# -*- coding: utf-8 -*-
"""Persistencia del índice: fragmentos + matriz de embeddings.

Guarda un hash por archivo para que al agregar un .md nuevo (o modificar uno)
solo se re-embeban los fragmentos que de verdad cambiaron. El cache por hash
de fragmento evita recalcular embeddings de textos que ya estaban.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np

from . import config
from .chunker import Fragmento, leer_corpus, texto_de_indexado


def hash_archivo(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()[:16]


class Store:
    def __init__(self, directorio: Path | None = None) -> None:
        self.directorio = Path(directorio or config.STORAGE_DIR)
        self.meta_path = self.directorio / "meta.json"
        self.vecs_path = self.directorio / "embeddings.npy"
        self.cache_path = self.directorio / "cache_embeddings.npz"
        self.fragmentos: list[Fragmento] = []
        self.vectores: np.ndarray = np.zeros((0, 0), dtype=np.float32)
        self.hash_archivos: dict[str, str] = {}
        self.modelo: str = config.EMBED_MODEL
        self.firma: str = self._firma()
        self.actualizado: str | None = None
        self._cache: dict[str, np.ndarray] = {}
        self.cargar()

    def _firma(self) -> str:
        """Identidad del embedding: si cambia modelo o prefijo, el cache se invalida."""
        from . import embeddings

        return f"{self.modelo}|{embeddings.PREFIJO_DOCUMENTO}|{embeddings.PREFIJO_CONSULTA}"

    # --- persistencia -------------------------------------------------------
    def cargar(self) -> None:
        if not self.meta_path.exists():
            return
        try:
            meta = json.loads(self.meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        self.fragmentos = [Fragmento(**f) for f in meta.get("fragmentos", [])]
        self.hash_archivos = meta.get("hash_archivos", {})
        self.modelo = meta.get("modelo", self.modelo)
        # Si el meta no tiene firma (indice anterior a esta version), el cache
        # se considera sospechoso y se rehace.
        self.firma = meta.get("firma", "")
        self.actualizado = meta.get("actualizado")
        if self.vecs_path.exists():
            try:
                self.vectores = np.load(self.vecs_path)
            except (OSError, ValueError):
                self.vectores = np.zeros((0, 0), dtype=np.float32)
        if self.cache_path.exists():
            try:
                datos = np.load(self.cache_path, allow_pickle=False)
                self._cache = {k: datos[k] for k in datos.files if k != "_firma"}
                # La firma viaja DENTRO del cache: meta y cache no pueden
                # desincronizarse entre si.
                firma_cache = str(datos["_firma"][0]) if "_firma" in datos.files else ""
                if firma_cache != self._firma():
                    self._cache = {}
            except (OSError, ValueError, KeyError, IndexError):
                self._cache = {}
        if self.firma != self._firma():
            # Cambió modelo o prefijo de embedding: los embeddings cacheados
            # ya no sirven y hay que rehacerlos.
            self._cache = {}
            self.firma = self._firma()

    def guardar(self) -> None:
        self.directorio.mkdir(parents=True, exist_ok=True)
        if self.vectores.size:
            np.save(self.vecs_path, self.vectores)
        elif self.vecs_path.exists():
            self.vecs_path.unlink()
        if self._cache:
            np.savez(
                self.cache_path,
                _firma=np.array([self.firma]),
                **self._cache,
            )
        elif self.cache_path.exists():
            self.cache_path.unlink()
        self.meta_path.write_text(
            json.dumps(
                {
                    "modelo": self.modelo,
                    "firma": self.firma,
                    "actualizado": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "hash_archivos": self.hash_archivos,
                    "fragmentos": [f.to_dict() for f in self.fragmentos],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    # --- indexado incremental ------------------------------------------------
    def indexar(self, forzar: bool = False, verbose: bool = True) -> dict:
        """Reindexa el corpus. Solo embebe lo que de verdad cambió."""
        if not config.BASE_DIR.exists():
            raise FileNotFoundError(f"No existe el corpus: {config.BASE_DIR}")

        archivos = sorted(config.BASE_DIR.glob("*.md"))
        hashes = {a.name: hash_archivo(a) for a in archivos}
        nombres = set(hashes)

        if forzar:
            self.fragmentos = []
            self.vectores = np.zeros((0, 0), dtype=np.float32)
            self.hash_archivos = {}

        cambiados = [
            a for a in archivos if self.hash_archivos.get(a.name) != hashes[a.name]
        ]
        # Archivos que estaban en el indice pero ya no existen en el corpus:
        # sus fragmentos tienen que desaparecer del indice.
        borrados = sorted(set(self.hash_archivos) - nombres)
        if not cambiados and not borrados and self.fragmentos:
            if verbose:
                print("El indice ya esta al dia (sin cambios en base-conocimiento).")
            return {
                "ok": True,
                "procesados": [],
                "borrados": [],
                "chunks": len(self.fragmentos),
                "duracion_s": 0.0,
                "sin_cambios": True,
            }

        from . import embeddings
        from .chunker import trocear_archivo

        if self.firma != self._firma():
            if verbose:
                print("Cambio en modelo/prefijo de embeddings: se rehace el cache.")
            self._cache = {}
            self.firma = self._firma()

        if verbose:
            print(
                f"Reindexando {len(cambiados)} archivo(s): "
                f"{', '.join(a.name for a in cambiados)}"
            )
        if borrados and verbose:
            print(f"Retirando del indice: {', '.join(borrados)}")

        # Se conservan los fragmentos de los archivos que no cambiaron.
        sets_cambiados = {a.name for a in cambiados}
        conservados = [
            f for f in self.fragmentos if f.archivo in nombres and f.archivo not in sets_cambiados
        ]
        nuevos_fragmentos: list[Fragmento] = []
        for archivo in cambiados:
            nuevos_fragmentos.extend(
                trocear_archivo(archivo, config.MAX_WORDS, config.MIN_WORDS)
            )

        fragmentos = sorted(
            conservados + nuevos_fragmentos,
            key=lambda f: (f.archivo, int(f.id.rsplit("::", 1)[-1])),
        )

        pendientes = [f for f in fragmentos if f.hash not in self._cache]
        if verbose:
            print(
                f"Fragmentos: {len(fragmentos)} | a embeber: {len(pendientes)} | "
                f"reusados del cache: {len(fragmentos) - len(pendientes)}"
            )

        if pendientes:
            textos = [texto_de_indexado(f) for f in pendientes]
            nuevos_vecs = embeddings.embed_textos(
                textos, modelo=self.modelo, prefijo=embeddings.PREFIJO_DOCUMENTO
            )
            for f, v in zip(pendientes, nuevos_vecs):
                self._cache[f.hash] = v.astype(np.float32)

        vectores = []
        for f in fragmentos:
            v = self._cache.get(f.hash)
            if v is None:
                raise RuntimeError(f"Sin embedding para {f.id}")
            vectores.append(v)

        self.fragmentos = fragmentos
        self.vectores = (
            embeddings.normalizar(np.asarray(vectores, dtype=np.float32))
            if vectores
            else np.zeros((0, 0), dtype=np.float32)
        )
        self.hash_archivos = hashes
        self.actualizado = time.strftime("%Y-%m-%dT%H:%M:%S")
        self.guardar()

        return {
            "ok": True,
            "procesados": [a.name for a in cambiados],
            "borrados": borrados,
            "chunks": len(self.fragmentos),
            "duracion_s": 0.0,
            "sin_cambios": False,
        }

    # --- utilidades ----------------------------------------------------------
    def documentos(self) -> list[dict]:
        conteo: dict[str, dict] = {}
        for f in self.fragmentos:
            info = conteo.setdefault(
                f.archivo,
                {
                    "archivo": f.archivo,
                    "documento": f.documento,
                    "chunks": 0,
                    "palabras": 0,
                    "hash": self.hash_archivos.get(f.archivo, ""),
                    "actualizado": self.actualizado,
                },
            )
            info["chunks"] += 1
            info["palabras"] += f.palabras
        return sorted(conteo.values(), key=lambda d: d["archivo"])

    @property
    def listo(self) -> bool:
        return bool(self.fragmentos) and self.vectores.shape[0] == len(self.fragmentos)
