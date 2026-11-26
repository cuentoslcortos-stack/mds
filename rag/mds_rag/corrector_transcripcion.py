# -*- coding: utf-8 -*-
"""Corrector de transcripcion: aplica las correcciones del analista ANTES de que
el modelo vea el material.

La regla 9 del protocolo dice que la frase erronea es un hecho del aparato de
registro, no un lapsus del sujeto. Dejar eso en manos del modelo es confiar en
que va a notar la correccion y aplicarla: en la calibracion NO lo hizo
(analizo "piga" como significante nodal, dos veces).

Aca se resuelve de forma determinista:

  1. se separa el discurso del sujeto de las anotaciones del analista;
  2. se detecta el par (forma erronea, forma correcta) en las anotaciones;
  3. se reemplaza la forma erronea por la correcta EN EL DISCURSO;
  4. se le devuelve al modelo la lista de correcciones aplicadas.

El modelo recibe el discurso ya corregido y una nota explicita de que la forma
erronea no es un significante suyo.
"""
from __future__ import annotations

import re

RE_QUOTES = re.compile(r'"([^"\n]{3,300})"')
RE_QUOTES_ALT = re.compile(r"«([^»\n]{3,300})»")

# Donde empiezan las anotaciones del analista. Si no se encuentra, se usa la
# primera marca de correccion.
RE_NOTAS = re.compile(
    r"(?im)^[^\n]{0,80}?"
    r"(?:correcciones?(?:\s+de\s+la\s+transcripci[oó]n)?|"
    r"notas?\s+(?:del\s+analista|del\s+usuario)|"
    r"contexto\s+(?:del\s+caso|extra)|"
    r"aclaraciones?|te\s+agrego|otra\s+cosa|datos\s+del\s+caso|"
    r"informaci[oó]n\s+del\s+caso|contexto)\s*[:.]"
)

# Marcas de que lo que viene entre comillas es el error del aparato.
MARCAS_ERROR = (
    "transcribi",
    "transcripci",
    "automático",
    "automatico",
    "mal ",
    "erróne",
    "errone",
    "equivoc",
    "mal聽",
    "se escuch",
)
# Marcas de que lo que viene entre comillas es lo que dijo el sujeto.
MARCAS_OK = (
    "dijo",
    "dice",
    "decía",
    "era ",
    "en realidad",
    "corrig",
    "correct",
    "verbatim",
    "textual",
)


def _norm(texto: str) -> str:
    return re.sub(r"\s+", " ", texto.lower()).strip()


def _candidatos(texto: str) -> list[tuple[int, int, str]]:
    """(inicio, fin, contenido) de cada fragmento entre comillas."""
    found: list[tuple[int, int, str]] = []
    for rx in (RE_QUOTES, RE_QUOTES_ALT):
        for m in rx.finditer(texto):
            found.append((m.start(1), m.end(1), m.group(1)))
    found.sort()
    return found


def _inicio_notas(texto: str) -> int:
    m = RE_NOTAS.search(texto)
    if m:
        return m.start()
    return len(texto)


def _marcador_mas_cercano(ventana: str) -> str | None:
    """Devuelve la marca (error/ok) MAS CERCANA al final de la ventana.

    Importa: la ventana de 220 chars puede contener las dos marcas. Si
    gana la equivocada, la forma correcta se clasifica como error.
    """
    mejor = None
    for tipo, marcas in (("error", MARCAS_ERROR), ("ok", MARCAS_OK)):
        for marca in marcas:
            pos = ventana.rfind(marca)
            if pos >= 0 and (mejor is None or pos > mejor[0]):
                mejor = (pos, tipo)
    return mejor[1] if mejor else None


def _clasificar(texto: str, citas: list[tuple[int, int, str]], desde: int) -> dict:
    """Separa las citas de las notas en 'erroneas' y 'correctas'."""
    erróneas: list[tuple[int, str]] = []
    correctas: list[tuple[int, str]] = []
    for inicio, fin, contenido in citas:
        if inicio < desde:
            continue
        ventana = _norm(texto[max(0, inicio - 220) : inicio])
        tipo = _marcador_mas_cercano(ventana)
        if tipo == "error":
            erróneas.append((inicio, contenido))
        elif tipo == "ok":
            correctas.append((inicio, contenido))
    return {"erroneas": erróneas, "correctas": correctas}


def aplicar(discurso: str, erronea: str, correcta: str) -> tuple[str, bool]:
    """Reemplaza la forma erronea por la correcta en el discurso del sujeto.

    Si la forma correcta trae "..." (el analista la abrevio), se usa el tramo
    final como ancla: se reemplaza el erroro MAS la cola redundante del
    discurso por la forma completa. "se me cayó una piga, se me puso a cargar
    porque la caída de pelo" queda "una piba me empezó a cargar porque la
    caída de pelo", y no una frase con el texto repetido dos veces.
    """
    patron = re.compile(re.escape(erronea), re.IGNORECASE)
    m = patron.search(discurso)
    if not m:
        return discurso, False

    if "..." in correcta:
        pre, _, post = correcta.partition("...")
        post = post.strip()
        if post:
            fin = discurso.find(post, m.end(), m.end() + 160)
            if fin > 0:
                nuevo = (
                    discurso[: m.start()]
                    + pre.strip()
                    + " "
                    + post
                    + discurso[fin + len(post) :]
                )
                return nuevo, True

    nuevo, n = patron.subn(correcta, discurso)
    return nuevo, n > 0


def separar_notas(texto: str) -> tuple[str, str]:
    """Separa el discurso del sujeto de las anotaciones del analista.

    Devuelve (discurso, notas). Todo lo que viene despues del primer bloque
    de anotaciones se considera anotacion: para el analisis lexico del sujeto
    solo cuenta el discurso.
    """
    i = _inicio_notas(texto)
    if i >= len(texto):
        return texto, ""
    return texto[:i], texto[i:]


def corregir(transcripcion: str) -> tuple[str, list[dict]]:
    """Devuelve (transcripcion corregida, lista de correcciones aplicadas)."""
    texto = transcripcion
    correcciones: list[dict] = []
    for _ in range(6):  # por si hay varias correcciones encadenadas
        inicio_notas = _inicio_notas(texto)
        citas = _candidatos(texto)
        clasif = _clasificar(texto, citas, inicio_notas)
        if not clasif["erroneas"]:
            break

        # Cada forma erronea se empareja con la forma correcta MAS CERCANA que
        # la sigue (por posicion, no por orden de lista).
        aplicadas = False
        for pos_err, erronea in clasif["erroneas"]:
            siguiente = None
            for pos_ok, contenido in clasif["correctas"]:
                if pos_ok > pos_err:
                    siguiente = contenido
                    break
            if siguiente is None:
                continue
            discurso = texto[:inicio_notas]
            resto = texto[inicio_notas:]
            discurso_nuevo, hubo = aplicar(discurso, erronea, siguiente)
            if hubo:
                texto = discurso_nuevo + resto
                correcciones.append(
                    {"erronea": erronea, "correcta": siguiente, "en_discurso": True}
                )
                aplicadas = True
        if not aplicadas:
            break
    return texto, correcciones


def bloque_correcciones(correcciones: list[dict]) -> str:
    """Bloque para el prompt: deja constancia de lo que se corrigio."""
    if not correcciones:
        return ""
    lineas = [
        "=== CORRECCIONES DE TRANSCRIPCION YA APLICADAS ===",
        "El sistema detecto y aplico estas correcciones del analista sobre el",
        "discurso del sujeto. La forma erronea NO es un significante del sujeto:",
        "no la analices como lapsus, no la cuentes en la Red, no la cites.",
    ]
    for c in correcciones:
        lineas.append(f'- "{c["erronea"]}"  ->  "{c["correcta"]}"')
    lineas.append("Trabajá sobre la forma corregida, que es la que está en el texto de arriba.")
    lineas.append("=== FIN DE LAS CORRECCIONES ===")
    return "\n".join(lineas)
