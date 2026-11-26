# -*- coding: utf-8 -*-
"""Troceado del corpus por jerarquía de títulos.

El corpus viene en Markdown ya estructurado: `## Capítulo X` y `### N. Subtema`.
Cortamos respetando esa jerarquía para que cada fragmento arrastre su
procedencia (documento > capítulo > sección), que es lo que permite citar
sin inventar. La sección `## Índice` se descarta: es un listado de capítulos
y solo agrega ruido al índice vectorial.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, asdict
from pathlib import Path

TITULO_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
TOC_RE = re.compile(
    r"^(indice|contenido|contenidos|sumario|index|table of contents)\b"
)
DOCO_RE = re.compile(r"^\*\*(.+?)\*\*\s*$")
FRASE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ¿¡\"'(])")


def sin_acentos(texto: str) -> str:
    norm = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in norm if not unicodedata.combining(c))


@dataclass
class Fragmento:
    """Un fragmento indexable con su procedencia."""

    id: str
    archivo: str
    documento: str
    capitulo: str
    seccion: str
    titulo: str
    texto: str
    palabras: int
    hash: str

    def to_dict(self) -> dict:
        return asdict(self)


def _documento(texto: str, respaldo: str) -> str:
    """Título del documento: la primera línea en negrita o el primer H1."""
    for linea in texto.split("\n")[:6]:
        linea = linea.strip()
        m = DOCO_RE.match(linea)
        if m:
            return m.group(1).strip()
        m = TITULO_RE.match(linea)
        if m:
            return m.group(2).strip()
    return respaldo


def parse_secciones(texto: str) -> list[tuple[list[tuple[int, str]], str]]:
    """Devuelve [([(nivel, titulo), ...], cuerpo), ...] respetando la jerarquía."""
    pila: dict[int, str] = {}
    cuerpo: list[str] = []
    secciones: list[tuple[list[tuple[int, str]], str]] = []
    ruta: list[tuple[int, str]] = []

    def cerrar() -> None:
        if any(linea.strip() for linea in cuerpo):
            secciones.append((list(ruta), "\n".join(cuerpo).strip()))
        cuerpo.clear()

    for linea in texto.split("\n"):
        m = TITULO_RE.match(linea)
        if m:
            cerrar()
            nivel = len(m.group(1))
            for clave in [k for k in pila if k >= nivel]:
                del pila[clave]
            pila[nivel] = m.group(2).strip()
            ruta = [(k, pila[k]) for k in sorted(pila)]
        else:
            cuerpo.append(linea)
    cerrar()
    return secciones


def _clasificar(ruta: list[tuple[int, str]]) -> tuple[str, str, str]:
    """Separa capítulo y sección según el nivel del título.

    El corpus usa H2 para el capítulo y H3+ para las secciones; algunos
    archivos arrancan con un H1 que es el título de la obra y no un capítulo.
    """
    if not ruta:
        return "", "", ""
    niveles = [n for n, _ in ruta]
    if 2 in niveles:
        capitulo = next(t for n, t in ruta if n == 2)
        resto = [t for n, t in ruta if n >= 3]
    else:
        capitulo = ruta[0][1]
        resto = [t for _, t in ruta[1:]]
    seccion = " > ".join(resto)
    titulo = " > ".join([capitulo] + resto)
    return capitulo, seccion, titulo


def _es_indice(ruta: list[tuple[int, str]]) -> bool:
    """La sección `## Índice` es un listado de capítulos: solo genera ruido."""
    if not ruta:
        return False
    return bool(TOC_RE.match(sin_acentos(ruta[-1][1]).strip().lower()))


def _partir_parrafo(parrafo: str, max_words: int) -> list[str]:
    """Un párrafo demasiado largo se parte por líneas y, si hace falta, por frases."""
    palabras = len(parrafo.split())
    if palabras <= max_words:
        return [parrafo]

    partes: list[str] = []
    buffer: list[str] = []
    n = 0
    for linea in parrafo.split("\n"):
        w = len(linea.split())
        if buffer and n + w > max_words:
            partes.append("\n".join(buffer))
            buffer, n = [], 0
        buffer.append(linea)
        n += w
    if buffer:
        partes.append("\n".join(buffer))

    refinado: list[str] = []
    for parte in partes:
        if len(parte.split()) <= max_words:
            refinado.append(parte)
            continue
        frases = [f for f in FRASE_RE.split(parte) if f.strip()]
        buffer, n = [], 0
        for frase in frases:
            w = len(frase.split())
            if buffer and n + w > max_words:
                refinado.append(" ".join(buffer))
                buffer, n = [], 0
            buffer.append(frase)
            n += w
        if buffer:
            refinado.append(" ".join(buffer))
    return refinado


def _trocear(cuerpo: str, max_words: int, min_words: int) -> list[str]:
    parrafos = [p.strip() for p in re.split(r"\n\s*\n", cuerpo) if p.strip()]
    atomicos: list[str] = []
    for parrafo in parrafos:
        atomicos.extend(_partir_parrafo(parrafo, max_words))

    trozos: list[str] = []
    buffer: list[str] = []
    n = 0
    for unidad in atomicos:
        w = len(unidad.split())
        if buffer and n + w > max_words:
            trozos.append("\n\n".join(buffer))
            buffer, n = [], 0
        buffer.append(unidad)
        n += w
    if buffer:
        trozos.append("\n\n".join(buffer))

    # Los restos muy chicos se fusionan con el trozo anterior.
    fusionados: list[str] = []
    for trozo in trozos:
        if fusionados and len(trozo.split()) < min_words:
            fusionados[-1] = fusionados[-1] + "\n\n" + trozo
        else:
            fusionados.append(trozo)
    return fusionados


def trocear_archivo(ruta: Path, max_words: int, min_words: int) -> list[Fragmento]:
    """Convierte un .md del corpus en fragmentos con jerarquía."""
    texto = ruta.read_text(encoding="utf-8")
    nombre = ruta.name
    documento = _documento(texto, nombre)

    fragmentos: list[Fragmento] = []
    for ruta_titulos, cuerpo in parse_secciones(texto):
        if _es_indice(ruta_titulos):
            continue
        # El preambulo previo al primer titulo es solo el encabezado del
        # documento: no aporta contenido y ensucia el indice.
        if not ruta_titulos and len(cuerpo.split()) < 80:
            continue
        capitulo, seccion, titulo = _clasificar(ruta_titulos)
        if not titulo:
            titulo = documento
        for i, trozo in enumerate(_trocear(cuerpo, max_words, min_words)):
            texto_frag = trozo.strip()
            if not texto_frag:
                continue
            etiqueta = f"{documento} | {titulo}" + (f" (cont. {i})" if i else "")
            digest = hashlib.sha256(f"{etiqueta}\n{texto_frag}".encode("utf-8")).hexdigest()[:16]
            fragmentos.append(
                Fragmento(
                    id=f"{nombre}::{len(fragmentos)}",
                    archivo=nombre,
                    documento=documento,
                    capitulo=capitulo,
                    seccion=seccion,
                    titulo=titulo + (f" (cont. {i})" if i else ""),
                    texto=texto_frag,
                    palabras=len(texto_frag.split()),
                    hash=digest,
                )
            )
    return fragmentos


def texto_de_indexado(fragmento: Fragmento) -> str:
    """Texto que se manda al modelo de embeddings (con contexto de procedencia)."""
    return f"{fragmento.documento} — {fragmento.titulo}\n{fragmento.texto}"


def leer_corpus(base_dir: Path, max_words: int, min_words: int) -> list[Fragmento]:
    fragmentos: list[Fragmento] = []
    for ruta in sorted(base_dir.glob("*.md")):
        fragmentos.extend(trocear_archivo(ruta, max_words, min_words))
    return fragmentos
