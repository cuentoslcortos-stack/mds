# -*- coding: utf-8 -*-
"""Analisis lexico del discurso: el trabajo determinista.

El protocolo MDS necesita repeticiones (la "Red"), cortes, vacilaciones y
raices compartidas. Eso no lo tiene que adivinar el modelo: se calcula aca y
se le pasa como dato, para que el modelo trabaje sobre material solido en vez
de inventar conteos.

Salida: un bloque de texto que se inyecta en el prompt del modo B.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter

# Palabras que, por si solas, describen un movimiento del discurso.
VACILACIONES = [
    "no sé", "capaz", "igual", "por otro lado", "de alguna manera",
    "o sea", "tipo", "quien sabe", "no sabría", "bueno", "mmm",
]
CORTE_PALABRA = re.compile(r"[¿?!]|\.\.\.|…|\b-ja\b|\b-mirá\b|\b-bueno\b")

# Raices de palabras vacias: se repiten siempre pero no dicen nada del sujeto.
# "porque x7" o "como x5" no son significantes: son la sintaxis del relato.
VACIAS_RAIZ = {
    "porq", "como", "pero", "para", "tien", "tene", "esti", "esto", "esta",
    "dije", "dice", "cosa", "pued", "hace", "hay", "much", "soli", "mas",
    "nada", "algo", "todo", "algui", "nadie", "bien", "ento", "ahor", "lueg",
    "pues", "tant", "vez", "cada", "dos", "tres", "dond", "cuan", "cual",
    "aqui", "alli", "asi", "sobr", "entr", "otra", "otro", "mism", "pode",
    "dente", "deci", "pens", "sabe", "quer", "ser", "estar", "muy", "solo",
    "tamb", "tien", "teng", "estu", "mien", "mire", "veo", "sien", "acer",
    "lleg", "qued", "vist", "gran", "cayo", "manda", "tenia", "haci",
    "sent", "caid", "cont", "comp", "empe", "agno", "ano", "mismo",
}

FRASES_SIN_VERBO = re.compile(
    r"\b(sin (querer|poder|saber)|no (sé|sabía|quise|quiero|puedo)|"
    r"capaz que|nada que|todo bien|re todo bien)\b"
)

TOKEN_RE = re.compile(r"[a-záéíóúñü0-9]+")


def _plano(texto: str) -> str:
    norm = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in norm if not unicodedata.combining(c))


def _raiz(token: str) -> str:
    """Raiz aproximada: los primeros 4 caracteres (agrupa flexiones)."""
    if len(token) < 5:
        return token
    return token[:4]


def _frases(texto: str) -> list[str]:
    partes = re.split(r"(?<=[.!?])\s+|\n+", texto)
    return [p.strip() for p in partes if p.strip()]


def _contar(texto_plano: str, forma: str) -> int:
    return len(re.findall(r"(?<![a-z])" + re.escape(forma) + r"(?![a-z])", texto_plano))


def analizar(transcripcion: str, max_significantes: int = 14) -> str:
    """Devuelve el bloque de datos lexicos para inyectar en el prompt."""
    texto = transcripcion.strip()
    plano = _plano(texto)
    frases = _frases(texto)
    planos_frases = [_plano(f) for f in frases]

    # --- 1) Raices con repeticion (la "Red" del protocolo) -------------------
    por_raiz: dict[str, list[tuple[str, str]]] = {}
    for frase, pfrase in zip(frases, planos_frases):
        for token in TOKEN_RE.findall(pfrase):
            if len(token) < 4:
                continue
            raiz = _raiz(token)
            por_raiz.setdefault(raiz, []).append((token, frase))

    repeticiones = []
    for raiz, usos in por_raiz.items():
        if len(usos) < 2:
            continue
        if raiz in VACIAS_RAIZ:
            continue
        conteo = Counter(u[0] for u in usos)
        formas = [t for t, _ in conteo.most_common()]
        repeticiones.append((len(usos), raiz, formas, [u[1] for u in usos]))

    # Se priorizan las que mas se repiten, con un empujon a las de cuerpo/edad
    # (en estos relatos suelen ser el nudo).
    keywords_pista = re.compile(
        r"abuel|viejo|pelo|panza|piba|joven|chic|carg|orden|herman|madre|padre"
        r"|amig|bro|escuel|facul|edat|dife|diferen|viech|golang|mirada|burla|barde"
    )
    repeticiones.sort(
        key=lambda r: (bool(keywords_pista.search(" ".join(r[2]))), r[0]), reverse=True
    )
    repeticiones = repeticiones[:max_significantes]

    # --- 2) Vacilaciones, cortes y apelaciones ------------------------------
    conteos_vac = []
    for forma in VACILACIONES:
        n = _contar(plano, _plano(forma))
        if n:
            conteos_vac.append((n, forma))
    conteos_vac.sort(reverse=True)

    n_puntos = len(re.findall(r"\.\.\.|…", texto))
    n_preguntas = len(re.findall(r"\?", texto))
    n_dudas = len(re.findall(r"\bno (sé|sabía|se|te|mí)\b", plano))

    # --- 3) Listas lexicales (cuerpo, edad, vinculos) ----------------------
    listas = {}
    for etiqueta, patron in [
        ("cuerpo/edad", r"pelo|panza|calvo|viejo|abuel|joven|chic|cuerpo|grueso"),
        ("vínculos", r"herman|madre|padre|amig|bro|compañer|chica|piba|chico| grupo|orden"),
        ("jerga", r"re |re$|re\b|para|quedarse|laburo|chamba|guaro|boludo|bardear|joda"),
    ]:
        palabras = []
        for token in TOKEN_RE.findall(plano):
            if re.fullmatch(patron, token) and token not in palabras:
                palabras.append(token)
        if palabras:
            listas[etiqueta] = palabras

    # --- 4) Armado del bloque ------------------------------------------------
    out: list[str] = []
    out.append("=== DATOS LEXICOS DEL DISCURSO (conteo automatico, no estimado) ===")

    if repeticiones:
        out.append("")
        out.append("SIGNIFICANTES CON REPETICION (raiz comun en el discurso):")
        for n, raiz, formas, contextos in repeticiones:
            variantes = ", ".join(formas[:6])
            out.append(f"- [{raiz}] x{n}  variantes: {variantes}")
            for contexto in contextos[:3]:
                limpio = " ".join(contexto.split())
                if len(limpio) > 150:
                    limpio = limpio[:150] + "..."
                out.append(f"    · {limpio}")
        out.append("")
        out.append(
            "Estos son los significantes que el protocolo exige trabajar en la Red: "
            "cada uno tiene al menos dos apariciones en registros distintos."
        )
    else:
        out.append("(sin repeticiones detectables)")

    out.append("")
    out.append("VACILACIONES, CORTES Y DUDAS:")
    if conteos_vac:
        for n, forma in conteos_vac[:8]:
            out.append(f"- «{forma}» x{n}")
    out.append(f"- puntos suspensivos / cortes: {n_puntos}")
    out.append(f"- signo de pregunta: {n_preguntas}")
    out.append(f"- negaciones del saber («no sé», «no sabía»…): {n_dudas}")

    # --- 3b) La Red: la lista para escribir el paso 2.3 ---------------------
    red: list[tuple[str, int, bool]] = []
    for n, raiz, formas, contextos in repeticiones:
        display = " / ".join(formas[:4])
        pista = bool(keywords_pista.search(display))
        red.append((display, n, pista))
    for n, forma in conteos_vac:
        if n >= 2 and not any(forma in d for d, _, _ in red):
            red.append((forma, n, True))
    red.sort(key=lambda r: (r[2], r[1]), reverse=True)
    red = red[:8]

    if red:
        out.append("")
        out.append("LA RED (significantes del discurso con su conteo EXACTO):")
        for display, n, _ in red:
            out.append(f"- «{display}» x{n}")
        out.append(
            "Estos son los significantes que tenes que trabajar en 2.2 y 2.3, con "
            "estos conteos exactos. No cuentes a mano y no inventes otros."
        )

    if listas:
        out.append("")
        out.append("VOCABULARIO POR CAMPO:")
        for etiqueta, palabras in listas.items():
            out.append(f"- {etiqueta}: {', '.join(palabras[:14])}")

    out.append("")
    out.append(
        "Estos conteos son exactos. Usalos como base para la Red y para la "
        "lectura de las repeticiones: no hace falta que cuentes a mano."
    )
    out.append("=== FIN DE LOS DATOS LEXICOS ===")
    return "\n".join(out)
