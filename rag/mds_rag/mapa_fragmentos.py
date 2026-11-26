# -*- coding: utf-8 -*-
"""Mapa de fragmentos: concepto lacaniano <-> fragmento <-> literal.

La fase 3.3 (Cotejo con la Teoria) pide, para cada concepto, el fragmento del
corpus donde ese concepto esta y el texto literal que lo sostiene. Eso NO es
interpretacion: es concordancia. Por eso se resuelve aca, de forma
determinista, y el modelo recibe el mapa hecho: concepto, fragmento y la frase
literal donde el concepto aparece.

El efecto sobre la calidad del informe es directo: la tabla 3.3 deja de ser
una lista de conceptos vagos con un numero pegado al lado y pasa a ser una
trazabilidad real, cita incluida.
"""
from __future__ import annotations

import re
import unicodedata

# --- Lexico lacaniano (terminologia del corpus en espanol) -------------------
# (nombre canonico, expresion regular). El orden importa: los mas
# especificos van primero porque el emparejamiento es por aparicion.
CONCEPTOS: list[tuple[str, str]] = [
    ("Primacia de la relacion sujeto-a-sujeto", r"relaci[oó]n de sujeto a sujeto|sujeto a sujeto|de sujeto a sujeto|primac[ií]a de la relaci"),
    ("Dialectica de la demanda y deseo del Otro", r"dial[eé]ctica de la demanda|deseo del otro|deseo del gran otro"),
    ("Ideal del Yo e identificacion secundaria", r"ideal del yo|identificaci[oó]n secundaria"),
    ("Estadio del espejo e identificacion imaginaria", r"estadio del espejo|imagen del espejo|formaci[oó]n de la imagen"),
    ("Agresividad y competition imaginaria", r"agresividad|competencia agresiva|concurrent|polarizaci"),
    ("Fetichizacion de la letra y vacios textuales", r"fetichiz|agujeros? textuales?|vac[ií]os? textuales?"),
    ("Nombre del Padre", r"nombre del padre|nombre-del-padre|padre simb[oó]lico"),
    ("Significante y significado", r"significante|significados?"),
    ("Cadena significante", r"cadena(?: de)? significante|cadena de significantes"),
    ("Falo y significacion falica", r"fal[oó]|falico"),
    ("Castracion y privacion", r"castraci[oó]n|privaci[oó]n"),
    ("Plus de gozar y goce", r"plus de gozar|m[aá]s de gozar|\bgoce\b|gozar|disfrute"),
    ("Deseo y falta", r"\bdeseo\b|faltar"),
    ("Fantasia del Otro", r"fantas[ií]a"),
    ("Objeto a y objeto pequeno", r"objeto a|objeto pequeño"),
    ("Sujeto y sujetividad", r"sujeto-supuesto|sujetividad|\bsujeto\b"),
    ("Lenguaje y discurso", r"\bhabla\b|lenguaje|discurso"),
    ("Inconsciente", r"inconsciente"),
    ("Imaginario, simbolico y real", r"lo imaginario|lo simb[oó]lico|lo real|registro simb"),
    ("Orden simbolico y ley", r"orden simb[oó]lico|ley simb[oó]lica"),
    ("Lacan: transgression", r"transgresi"),
    ("Deseo del otro y demanda", r"demanda"),
    ("Transferencia", r"transferencia"),
    ("Contratransferencia", r"contratransferencia"),
    ("Acting out", r"acting[ -]out"),
    ("Pasaje al acto", r"pasaje al acto"),
    ("Sintoma", r"s[ií]ntoma"),
    ("Formacion de compromiso", r"formaci[oó]n de compromiso"),
    ("Histeria", r"histeria|hist[eé]rica|isteri"),
    ("Obsesion", r"obsesi[oó]n|obsesivo"),
    ("Psicosis", r"psicosis|psic[oó]tico"),
    ("Neurosis", r"neurosis"),
    ("Metafora y metonimia", r"metafora|metonimia|metonimia"),
    ("Punto de goce", r"punto de goce"),
    ("Bourgeois y sindrome", r"bourgeois|s[ií]ndrome"),
    ("Sujeto supuesto saber", r"sujeto que supone saber|saber supuest"),
    ("Significacion del Nombre", r"significaci[oó]n del nombre"),
    ("Mirada y mirada del objeto a", r"mirada"),
]

RE_FRASE = re.compile(r"(?<=[.!?;:])\s+|\n+")
_LITERAL_MAX = 190
_VENTANA_ANTES = 80
_VENTANA_DESPUES = 120

# El mismo patron, compilado para que también matchee el texto ORIGINAL
# (con acentos): así se puede-centered la cita en la palabra que la activa.
_VOCALES = {"a": "[aá]", "e": "[eé]", "i": "[ií]", "o": "[oó]", "u": "[uú]", "n": "[nñ]"}


def _expandir(patron: str) -> str:
    """Hace el patron insensible a acentos sin romper las clases existentes."""
    out: list[str] = []
    i = 0
    while i < len(patron):
        c = patron[i]
        if c == "\\":
            out.append(patron[i : i + 2])
            i += 2
            continue
        if c == "[":
            fin = patron.find("]", i)
            if fin > 0:
                out.append(patron[i : fin + 1])
                i = fin + 1
                continue
        if c in _VOCALES:
            out.append(_VOCALES[c])
        else:
            out.append(c)
        i += 1
    return "".join(out)


_RX: dict[str, re.Pattern] = {
    nombre: re.compile(_expandir(patron)) for nombre, patron in CONCEPTOS
}


def _ventana(frase: str, posicion: int) -> str:
    """Recorta la frase alrededor de la palabra que activa el concepto.

    Importa: si la cita se corta donde empieza el texto, el modelo no ve la
    palabra que justifica el concepto y no puede copiarla con confianza.
    """
    inicio = max(0, posicion - _VENTANA_ANTES)
    fin = min(len(frase), posicion + _VENTANA_DESPUES)
    trozo = frase[inicio:fin]
    if inicio > 0:
        trozo = "..." + trozo
    if fin < len(frase):
        trozo = trozo + "..."
    return re.sub(r"\s+", " ", trozo).strip()


def _norm(texto: str) -> str:
    norm = unicodedata.normalize("NFKD", texto.lower())
    plano = "".join(c for c in norm if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", plano).strip()


def _frases(texto: str) -> list[str]:
    partes = RE_FRASE.split(texto)
    return [p.strip() for p in partes if p and len(p.strip()) > 12]


def _limpiar(frase: str) -> str:
    """Deja la frase apta para ser copiada dentro de una celda de tabla."""
    limpio = re.sub(r"\s+", " ", frase).strip()
    # El corpus viene en markdown: la cita tiene que salir limpia.
    limpio = re.sub(r"^[>\-\*#\s]+", "", limpio)
    limpio = re.sub(r"\*{1,2}", "", limpio)
    limpio = limpio.replace("|", "/").replace('"', "'")
    if len(limpio) > _LITERAL_MAX:
        corte = limpio.rfind(" ", 0, _LITERAL_MAX)
        limpio = limpio[: corte if corte > 60 else _LITERAL_MAX] + "..."
    return limpio


def conceptos_de(texto: str) -> list[tuple[str, str]]:
    """Conceptos presentes en un fragmento, con la frase que los sostiene."""
    frases = _frases(texto)
    hallados: list[tuple[str, str]] = []
    vistos: set[str] = set()
    for nombre in _RX:
        if nombre in vistos:
            continue
        rx = _RX[nombre]
        for frase in frases:
            m = rx.search(frase)
            if m:
                hallados.append((nombre, _limpiar(_ventana(frase, m.start()))))
                vistos.add(nombre)
                break
    return hallados


def mapa_conceptos(resultados: list[dict]) -> dict[str, list[tuple[int, str]]]:
    """concepto -> [(numero de fragmento, frase literal), ...]."""
    por_concepto: dict[str, list[tuple[int, str]]] = {}
    for i, r in enumerate(resultados, start=1):
        for nombre, frase in conceptos_de(r.get("texto", "")):
            por_concepto.setdefault(nombre, []).append((i, frase))
    return por_concepto


def _solape(a: str, b: str) -> int:
    """Palabras en comun entre dos nombres de concepto."""
    pa = set(re.findall(r"[a-záéíóúñ]{4,}", a.lower()))
    pb = set(re.findall(r"[a-záéíóúñ]{4,}", b.lower()))
    return len(pa & pb)


def _numero(celda: str) -> int | None:
    """El numero de fragmento que el modelo puso en la celda."""
    m = re.search(r"(\d{1,2})", celda)
    return int(m.group(1)) if m else None


def completar_cotejo(texto: str, resultados: list[dict]) -> str:
    """Le pone a cada fila de la tabla 3.3 el literal de su fragmento.

    El modelo dice QUE concepto usa y DE QUE fragmento. El literal se
    resuelve por concordancia sobre el corpus: se busca el concepto del mapa
    que mejor coincide con el de la fila y se escribe la cita textual real,
    con su numero de fragmento. Asi la tabla no dice "el concepto viene de
    aqui" con la palabra del modelo, sino con el texto del corpus.
    """
    if not resultados:
        return texto
    mapa = mapa_conceptos(resultados)
    if not mapa:
        return texto

    lineas = texto.split("\n")
    dentro = False
    cabeceras: list[str] = []
    sangria = ""
    salida: list[str] = []

    for linea in lineas:
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        es_fila = linea.strip().startswith("|") and len(lineas) > 0
        if es_fila and "Concepto lacaniano" in linea and "Fragmento" in linea:
            dentro = True
            cabeceras = celdas
            sangria = linea[: len(linea) - len(linea.lstrip())]
            salida.append(linea)
            continue
        if dentro:
            separador = all(set(c) <= set("-: ") for c in celdas if c)
            if separador and len(celdas) == len(cabeceras):
                salida.append(linea)
                continue
            if not es_fila or len(celdas) != len(cabeceras):
                dentro = False
                salida.append(linea)
                continue
            # Fila de datos: se le busca el literal del concepto.
            concepto = celdas[0]
            if ":" not in celdas[1]:
                elegido = None
                mejor_puntaje = 0
                for nombre, usos in mapa.items():
                    puntaje = _solape(concepto, nombre)
                    if puntaje > mejor_puntaje:
                        mejor_puntaje = puntaje
                        elegido = (nombre, usos)
                if elegido and mejor_puntaje >= 1:
                    nombre, usos = elegido
                    # Si el modelo ya habia pointing a un fragmento que tiene
                    # ese concepto, se respeta ese: el numero es suyo.
                    frag = None
                    pedido = _numero(celdas[1])
                    for i, frase in usos:
                        if i == pedido:
                            frag = (i, frase)
                            break
                    if frag is None:
                        frag = usos[0]
                    celdas[1] = f'[{frag[0]}: "{frag[1]}"]'
            sangria_fila = linea[: len(linea) - len(linea.lstrip())] or sangria
            salida.append(sangria_fila + "| " + " | ".join(celdas) + " |")
            continue
        salida.append(linea)

    return "\n".join(salida)


def armar(resultados: list[dict]) -> str:
    """Arma el bloque MAPA DE FRAGMENTOS para el prompt.

    `resultados` es la lista de dicts que devuelve Recuperador.buscar().

    La salida es POR CONCEPTO (no por fragmento): una linea por concepto
    lacaniano detectado, con el numero del fragmento donde aparece y la frase
    literal del corpus que lo sostiene. Asi la tabla 3.3 del informe se arma
    copiando, no adivinando.
    """
    if not resultados:
        return (
            "=== MAPA DE FRAGMENTOS ===\n"
            "(no se recuperaron fragmentos)\n"
            "=== FIN DEL MAPA DE FRAGMENTOS ==="
        )

    lineas = [
        "=== MAPA DE FRAGMENTOS (concordancia literal, calculada) ===",
        "Cada linea dice que concepto lacaniano aparece en que fragmento y en",
        "que frase literal del corpus. Son datos, no interpretacion: el fragmento",
        "de la tabla 3.3 ya esta resuelto, solo hay que explicar que le hace al",
        "discurso del sujeto.",
        "",
        "FRAGMENTOS RECUPERADOS:",
    ]
    for i, r in enumerate(resultados, start=1):
        ubicacion = r.get("capitulo") or ""
        if r.get("seccion"):
            ubicacion = f"{ubicacion} > {r['seccion']}" if ubicacion else r["seccion"]
        lineas.append(f"  [{i}] {r.get('documento', '')} — {ubicacion}".rstrip(" —"))

    por_concepto: dict[str, list[tuple[int, str]]] = {}
    for i, r in enumerate(resultados, start=1):
        for nombre, frase in conceptos_de(r.get("texto", "")):
            por_concepto.setdefault(nombre, []).append((i, frase))

    orden = sorted(por_concepto.items(), key=lambda kv: (-len(kv[1]), kv[0]))

    lineas.append("")
    lineas.append("CONCEPTOS DETECTADOS (concepto → fragmento → literal):")
    if not orden:
        lineas.append("  (ninguno)")
    for nombre, usos in orden:
        i, frase = usos[0]
        otros = ", ".join(str(u[0]) for u in usos[1:4])
        sufijo = f" — tambien en [{otros}]" if otros else ""
        literal = frase if len(frase) <= 170 else frase[:167] + "..."
        lineas.append(f'- {nombre} → [{i}]{sufijo}  "{literal}"')

    lineas.append("")
    lineas.append(
        f"Son {len(resultados)} fragmentos recuperados: la tabla 3.3 tiene "
        f"{len(resultados)} filas, una por fragmento. Usá todos: los N "
        "fragmentos son parte del informe."
    )
    lineas.append(
        "Regla de uso: elegí de esta lista los conceptos que sostienen el "
        "nucleo del malestar. Para cada uno: numero de fragmento en la columna "
        "Fragmento y la frase literal entre comillas dobles en la celda, tal "
        "cual aparece arriba."
    )
    lineas.append("=== FIN DEL MAPA DE FRAGMENTOS ===")
    return "\n".join(lineas)
