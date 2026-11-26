# -*- coding: utf-8 -*-
"""Verificador de citas: comprueba que lo citado exista LITERALMENTE.

Un modelo de 12B puede parafrasear un fragmento del corpus y presentarlo
como cita textual. El informe MDS miente si eso pasa: la cita es el unico
puente verificable entre la teoria y el caso.

Este modulo hace la comprobaciondeterministica DESPUES de generar:

  * la cita literal existe en el fragmento que se cita       -> verificada
  * la cita existe en OTRO fragmento                        -> se reatribuye
  * la cita no existe pero comparte palabras con una frase
    real del corpus                                         -> se repara
    con el literal del corpus
  * la cita no se parece a nada del corpus                  -> se deja (puede
    ser una cita del discurso del sujeto, que es legitima)

Que la cuarta opcion exista es lo que hace seguro el modulo: no toca las
citas del sujeto ("abuelo", "me senti para el orto"), porque no comparten
palabras con el corpus.

El criterio de "se parece" es el SOLAPAMIENTO DE PALABRAS DE CONTENIDO, no
una similitud de caracteres: dos frases pueden parecerse mucho en letras y
no decir nada la una de la otra.
"""
from __future__ import annotations

import difflib
import re
import unicodedata

# Marcador de cita: [n] o [n: "literal"] o [n: «literal»]
RE_MARCA = re.compile(r"\[(\d{1,2})([^\]\n]{0,340}?)\]")
RE_QUOTE = re.compile(r"[:：]\s*[«\"']\s*(.+?)\s*[»\"']\s*$", re.DOTALL)
RE_QUOTE_SUELTO = re.compile(r"[«\"]([^«»\"]{8,400}?)[»\"]")
RE_FRASE = re.compile(r"(?<=[.!?;:])\s+|\n+")

# Palabras que no sirven para medir parecido: aparecen en todos lados.
VACIAS = {
    "este", "esta", "esto", "ese", "esa", "eso", "aquel", "aquella", "todo",
    "toda", "todos", "todas", "otro", "otra", "mismo", "misma", "cual",
    "cuando", "donde", "como", "cuando", "porque", "para", "pero", "cada",
    "entre", "sobre", "tambien", "entonces", "ahora", "luego", "pues",
    "tiene", "tienen", "tengo", "hacen", "hacer", "puede", "pueden", "dice",
    "dicho", "dicen", "dije", "dijo", "mas", "muy", "solo", "sin", "algo",
    "nada", "alguien", "nadie", "todo", "toda", "bien", "asi", "aqui",
    "alli", "cual", "quien", "cuyo", "cuya", "unos", "unas", "unos",
    "decir", "decir", "veces", "vez", "cosa", "cosas", "forma", "parte",
}

UMBRAL_REPARO_SIM = 0.55
UMBRAL_REPARO_PALABRAS = 0.5
UMBRAL_SOSPECHOSO = 0.34
LARGO_LITERAL = 220


def _norm(texto: str) -> str:
    norm = unicodedata.normalize("NFKD", texto.lower())
    plano = "".join(c for c in norm if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", plano).strip()


def _contenido(texto: str) -> set[str]:
    """Palabras de contenido (las que порran el significado)."""
    return {
        t
        for t in _norm(texto).split()
        if len(t) >= 5 and t not in VACIAS
    }


def _frases(texto: str) -> list[str]:
    partes = RE_FRASE.split(texto)
    return [p.strip() for p in partes if p and len(p.strip()) > 15]


def _literal(frase: str) -> str:
    limpio = re.sub(r"\s+", " ", frase).strip()
    limpio = re.sub(r"^[>\-\*#\s]+", "", limpio)
    limpio = re.sub(r"\*{1,2}", "", limpio)
    limpio = limpio.replace("|", "/").replace('"', "'")
    if len(limpio) > LARGO_LITERAL:
        corte = limpio.rfind(" ", 0, LARGO_LITERAL)
        limpio = limpio[: corte if corte > 60 else LARGO_LITERAL] + "..."
    return limpio


class _Fragmentos:
    """Vista normalizada del corpus recuperado, para comparar rapido."""

    def __init__(self, resultados: list[dict]) -> None:
        self.textos: list[str] = []
        for r in resultados:
            # Se busca tambien en los metadatos: los titulos de seccion del
            # corpus son frases del Lacan y el modelo las cita textualmente.
            partes = [
                r.get("texto", ""),
                r.get("titulo", ""),
                r.get("seccion", ""),
                r.get("capitulo", ""),
            ]
            self.textos.append(" \n ".join(p for p in partes if p))
        self.normas = [_norm(t) for t in self.textos]
        self.frases = [_frases(t) for t in self.textos]
        self.contenido_frases = [[_contenido(f) for f in fs] for fs in self.frases]

    def contiene(self, indice: int, cita: str) -> bool:
        """True si `cita` aparece literal en el fragmento `indice` (0-based)."""
        if indice < 0 or indice >= len(self.normas):
            return False
        n = _norm(cita)
        return bool(n) and n in self.normas[indice]

    def donde_esta(self, cita: str) -> int | None:
        """Indice (0-based) del fragmento donde la cita aparece literal."""
        n = _norm(cita)
        if not n:
            return None
        for i, texto in enumerate(self.normas):
            if n in texto:
                return i
        return None

    def solapamiento(self, cita: str, frase: str) -> float:
        """Fraccion de las palabras de contenido de la cita que estan en la frase."""
        palabras = _contenido(cita)
        if not palabras:
            return 0.0
        presentes = _contenido(frase)
        return len(palabras & presentes) / len(palabras)

    def max_solapamiento(self, cita: str) -> float:
        """Mayor solapamiento de la cita con cualquier fragmento del corpus."""
        mejor = 0.0
        for i, frases in enumerate(self.frases):
            for frase in frases:
                solape = self.solapamiento(cita, frase)
                if solape > mejor:
                    mejor = solape
        return mejor

    def mas_parecido(self, cita: str) -> tuple[int, str, float] | None:
        """(fragmento, frase, solapamiento) de la frase del corpus mas parecida.

        Solo se consideran candidatas las frases que comparten al menos la
        mitad de las palabras de contenido de la cita: el parecido de
        caracteres solo sirve para desempatar.
        """
        n = _norm(cita)
        if not n:
            return None
        mejor = None
        mejor_key = (0.0, 0.0)
        for i, frases in enumerate(self.frases):
            for j, frase in enumerate(frases):
                solape = self.solapamiento(cita, frase)
                if solape < UMBRAL_REPARO_PALABRAS:
                    continue
                ratio = difflib.SequenceMatcher(None, n, _norm(frase)).ratio()
                if ratio < UMBRAL_REPARO_SIM:
                    continue
                clave = (solape, ratio)
                if clave > mejor_key:
                    mejor_key = clave
                    mejor = (i, frase, solape)
        return mejor


def _resolver(frags: _Fragmentos, indice: int, cita: str, stats: dict) -> str:
    """Devuelve el marcador corregido para una cita con texto."""
    if frags.contiene(indice - 1, cita):
        stats["verificadas"] += 1
        return ""
    donde = frags.donde_esta(cita)
    if donde is not None:
        # La cita es literal, pero de otro fragmento: se reatribuye.
        stats["reatribuidas"] += 1
        return f"[{donde + 1}: {_literal(cita)}]"
    parecido = frags.mas_parecido(cita)
    if parecido:
        i, frase, _ = parecido
        stats["reparadas"] += 1
        return f"[{i + 1}: {_literal(frase)}]"
    # Sin sosteno literal: se deja como estaba, pero se cuenta como sospechosa
    # solo si parece una cita del corpus (comparte palabras con el).
    if frags.max_solapamiento(cita) >= UMBRAL_SOSPECHOSO:
        stats["ajenas"] += 1
    else:
        stats["propias"] += 1
    return ""


def verificar(texto: str, resultados: list[dict]) -> tuple[str, dict]:
    """Corrige las citas del informe y devuelve (texto, estadisticas)."""
    frags = _Fragmentos(resultados)
    stats = {
        "citas": 0,
        "verificadas": 0,
        "reatribuidas": 0,
        "reparadas": 0,
        "sin_literal": 0,
        "ajenas": 0,
        "propias": 0,
    }
    if not texto.strip():
        return texto, stats

    piezas: list[str] = []
    ultimo = 0
    for marca in RE_MARCA.finditer(texto):
        indice = int(marca.group(1))
        cola = marca.group(2) or ""
        piezas.append(texto[ultimo : marca.start()])
        ultimo = marca.end()
        stats["citas"] += 1

        cita = None
        m = RE_QUOTE.search(cola)
        if m:
            cita = m.group(1).strip()
        elif ":" in cola:
            # Cita sin comillas: [10: agresividad estructural hacia el otro].
            # Tambien se verifica: si no es literal, se repara con el texto
            # real del corpus (y queda entre comillas).
            resto = cola.split(":", 1)[1].strip().strip("«»\"'")
            if 5 <= len(resto) <= 300:
                cita = resto

        if cita:
            correccion = _resolver(frags, indice, cita, stats)
            piezas.append(correccion or marca.group(0))
            continue

        # Cita sin literal adentro: no se toca. El formato que exige la
        # regla 13 es [n: "literal"], asi que una cita suelta se deja como
        # esta (puede ser una cita del discurso del sujeto).
        stats["sin_literal"] += 1
        piezas.append(marca.group(0))

    piezas.append(texto[ultimo:])
    return "".join(piezas), stats
