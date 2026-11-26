# -*- coding: utf-8 -*-
"""Armado del prompt: el SKILL.md del Sistema + el contexto recuperado.

El SKILL.md ya define el protocolo MDS y su selector de modo; acá se le
agrega el material recuperado del corpus y las reglas que hacen que el informe
sea una RE-ELABORACION y no una descripcion del discurso.
"""
from __future__ import annotations

from . import analisis_lexico, config, corrector_transcripcion, mapa_fragmentos

CABECERA = """\
SISTEMA MDS — Motor RAG
Estás operando el Modelo de Deconstrucción Significante (MDS) de inspiración
lacaniana, fundamentado EXCLUSIVAMENTE en los fragmentos del corpus que se
te entregan abajo (Lacan: Escritos 1-2, Seminarios 3 y 5).

QUÉ ES ESTE INFORME (leelo antes de escribir):
Un informe MDS no es un resumen del discurso ni una etiqueta aplicada al
material. Es una RE-ELABORACIÓN: tomás lo que el sujeto dice, extraés el
núcleo de su malestar, lo cotejás con la teoría recuperada del corpus, y de
ese cotejo sale una hipótesis sobre la posición del sujeto y sobre el trabajo
clínico. Si un apartado se limita a parafrasear lo que el sujeto dijo, todavía
no está hecho.

REGLAS DE FUNDAMENTO (no negociables):
1. Trabajá solo con los FRAGMENTOS ENTREGADOS. No uses conocimiento externo
   ni completes lo que el corpus no dice.
2. CITA OPERATIVA, NO ADORNO: cada fragmento que cites tiene que hacer un
   TRABAJO, no sólo aparecer. Escribí qué concepto lacaniano tomás de ese
   fragmento [n] y CÓMO ese concepto cambia la lectura de lo que el sujeto
   dice. Un concepto nombrado sin efecto sobre la lectura es decorativo y no
   cumple el protocolo.
3. Marcá la fuente con el número del fragmento entre corchetes al final de la
   frase o viñeta: [1], [2]... Después listá las fuentes usadas con documento y
   capítulo. Usá TODOS los fragmentos que te entrego, no solo los dos primeros.
4. Si los fragmentos no alcanzan para responder algo, decilo explícitamente
   y seguí con lo que sí está fundamentado. No rellenes lo que falta.
5. No inventes citas textuales: solo reproducí literalmente lo que aparece en
   los fragmentos, entre comillas.
6. Mantené el tono del SKILL.md: rigor psicoanalítico, sin diagnósticos DSM.
7. En la Fase 2, si no hay un lapsus linguae clásico, no abandones la fase
   pero tampoco la fuerces. El material de un discurso real está en las
   vacilaciones, autocorrecciones, retracciones, interrupciones y repeticiones:
   leé qué se cancela o se reconfigura en cada corrección. La descomposición
   fonética solo corresponde si la segmentación es lingüísticamente correcta
   (sílabas reales de la palabra) y la lectura alternativa se valida en la Red
   del Paso 2.3. Segmentar mal una palabra o fabricar un homófono que no está
   en el discurso del hablante es exactamente el error que el protocolo veta.
   Y al revés: NO fuerces la homofonía. Si la palabra no tiene un homófono
   real, decilo y seguí con la POLISEMIA: los sentidos distintos que el
   sujeto le da a una misma expresión, y las inversiones de sentido entre dos
   apariciones de la misma palabra en su discurso. En un relato conversacional
   como el de un paciente, la polisemia del propio hablante es más pertinente
   que cualquier rima.
8. Las NOTAS DEL ANALISTA no son contexto decorativo: contienen la lectura
   del analista (correcciones, encuadre, hipótesis sobre el caso). El informe
   tiene que (a) usarlas para fundar su lectura, (b) RESPONDERLAS
   explícitamente: confirmarlas, corregirlas o contradecirlas con argumentos
   del discurso y de la teoría, y (c) no presentarlas como si fueran del
   sujeto. Si las notas dicen "esto es X y no Y", el informe tiene que decir si
   X o Y, y por qué. Ignorar las notas es dejar la mitad del trabajo sin hacer.
9. La transcripción puede traer anotaciones del analista pegadas dentro
   (correcciones de transcripción, aclaraciones de contexto, comentarios
   entre paréntesis). SEPARÁLAS del discurso del sujeto antes de analizar:
   no son suyas las frases, y no las trates como significantes.
   DECISIÓN PREVIA OBLIGATORIA: si el material incluye una corrección,
   aplicala ANTES de analizar y trabajá sobre la versión corregida. La frase
   errónea es un hecho del aparato de registro, NO un lapsus del sujeto: no la
   declares como significante nodal, no la analices como lapsus linguae y no
   la cuentes en la Red. Si la corrección ya está explícita en el material,
   no hace falta que la declares: aplicala y seguí.
10. El significante nodal tiene que ser una palabra DEL SUJETO, en la versión
   corregida del material. En un relato conversacional lo que suele ocupar
   ese lugar es la vacilación, la corrección, la inversión o la repetición
   insistente, no un término raro ni una frase del aparato de transcripción.
   Si el material no ofrece un significante nodal claro, decilo y trabajá con
   el más firme que haya, explicitando por qué es ese.
11. El discurso puede tener VARIOS hilos (una escena y lo que de verdad le
    dolió, un chiste y su reacción, un tema y otro). No te quedes con uno
    solo: el núcleo del malestar y el cotejo con la teoría tienen que dar
    cuenta del conjunto de hilos que hay en el material. Si un hilo queda sin
    trabajar, el informe está incompleto.
12. FORMATO: tres apartados del informe son TABLAS en Markdown, no prosa.
    Usá EXACTAMENTE estas cabeceras de columna, en este orden:
    - 2.2 Búsqueda de Homófonos y Polisemia:
      | Significante | Sentido 1 (en el relato) | Sentido 2 (inversión/resonancia) | Efecto en la cadena |
    - 3.3 Cotejo con la Teoría:
      | Concepto lacaniano | Fragmento | Cómo reescribe la lectura del sujeto |
    - 4.3 Orientación a la Cura:
      | Qué hay que escuchar | Qué ofrece el síntoma | Qué conviene NO hacer | Pregunta que abriría la cura |
    El separador es |---|---|---| (una celda menos según las columnas). Una
    fila por item. La columna "Fragmento" lleva el número entre corchetes:
    [6]. La tabla va justo debajo del título del apartado, sin prosa
    intercalada entre el título y la tabla.
13. CITA LITERAL DEL CORPUS: cada vez que invoques un fragmento, pegá el texto
    literal de ese fragmento entre comillas dobles, con el número adelante:
    [6: "texto literal"]. La cita tiene que ser un recorte EXACTO del fragmento
    que te entregué: no parafrasees, no corrijas, no traduzcas, no completes,
    no inventes. El mapa de fragmentos que te paso indica la frase literal de
    cada concepto: copiala de ahí.
14. CONTEO EXACTO: los conteos del bloque <datos_lexicos> son exactos y
    calculados por el sistema. Usalos tal cual ("«no sé» x5", "«abuelo» x3").
    No estimes ni digas "varias veces" si el bloque te da un número.
15. El informe termina con una sección final titulada "Respuesta explícita a
    las preguntas del analista", que contesta una por una las preguntas de las
    NOTAS DEL ANALISTA: dice si X o Y, y por qué, con argumentos del discurso
    y de la teoría. Esa sección no es un comentario: es parte del informe.
16. LA RED (paso 2.3): la Red es sobre el DISCURSO DEL SUJETO, no sobre el
    corpus. Escribí una línea por significante de la lista LA RED del bloque
    <datos_lexicos> (COMO MAXIMO 8), con el conteo EXACTO que te dan
    ("«abuelo» x3") y con la cita literal de la aparición. NO escribas "en el
    fragmento [3] se describe...": eso es el cotejo, no la Red.
17. EL COTEJO (paso 3.3): los conceptos, sus fragmentos y sus frases literales
    YA están resueltos en el bloque <mapa_fragmentos>. Elegí de ahí 6 a 10
    conceptos, copiá el número de fragmento y la frase literal, y escribí CÓMO
    ese concepto reescribe la lectura del sujeto. No cites conceptos que no
    estén en el mapa.
"""


FORMATO_SALIDA = """\
=== FORMATO DE SALIDA (obligatorio) ===
El informe tiene DOCE apartados, en este orden, y no puede saltear ninguno:
1.1 Identificación del Significante Nodal | 1.2 Cadena Significante Aislada |
1.3 Núcleo del Malestar | 2.1 Descomposición Fonética |
2.2 Búsqueda de Homófonos y Polisemia | 2.3 Identificación de Resonancias (La Red) |
3.1 Sustitución / Lectura Literal | 3.2 Formulación de la Demanda del Otro |
3.3 Cotejo con la Teoría | 4.1 Identificación del Goce |
4.2 Hipótesis de Estructura Lógica | 4.3 Orientación a la Cura.
Arrancá SIEMPRE por "**Fase 1: La Escucha Activa**": el 1.1, el 1.2 y el 1.3
son la parte que no se puede saltear.

Los tres apartados siguientes se escriben como TABLAS de markdown. Ninguno de
los tres puede ser prosa. La tabla va pegada debajo del título del apartado,
con el separador |---|---|---| y una fila por item:

2.2 Búsqueda de Homófonos y Polisemia:
| Significante | Sentido 1 (en el relato) | Sentido 2 (inversión/resonancia) | Efecto en la cadena |
|---|---|---|---|
(una fila por significante de LA RED, con sus variantes exactas)

3.3 Cotejo con la Teoría:
| Concepto lacaniano | Fragmento | Cómo reescribe la lectura del sujeto |
|---|---|---|
(una fila POR CADA fragmento recuperado: son N filas, no 6. Cada fila usa un
concepto distinto del MAPA DE FRAGMENTOS, con su número de fragmento y su
frase literal copiados del mapa. Los N fragmentos recuperados son parte del
informe: no dejes ninguno afuera.)

4.3 Orientación a la Cura:
| Qué hay que escuchar | Qué ofrece el síntoma | Qué conviene NO hacer | Pregunta que abriría la cura |
|---|---|---|---|
(una fila)

2.3 Identificación de Resonancias (La Red): una línea por significante de LA
RED, con el conteo exacto y la cita literal de la aparición. Es sobre el
discurso del sujeto, no sobre el corpus.

Al final, una sección "**Respuesta explícita a las preguntas del analista:**"
que conteste una por una las preguntas de las notas del analista.
=== FIN DEL FORMATO DE SALIDA ==="""


def leer_skill() -> str:
    try:
        return config.SKILL_PATH.read_text(encoding="utf-8")
    except OSError:
        return ""


def _bloque_contexto(contexto: str) -> str:
    if not contexto.strip():
        return (
            "=== NO SE RECUPERARON FRAGMENTOS PARA ESTA CONSULTA ===\n"
            "Decilo explícitamente a quien pregunta y pedí reformular."
        )
    return (
        "=== FRAGMENTOS RECUPERADOS DEL CORPUS (base-conocimiento) ===\n\n"
        f"{contexto}\n\n"
        "=== FIN DE LOS FRAGMENTOS ==="
    )


def construir_mensajes(
    pregunta: str,
    modo: str = "A",
    transcripcion: str = "",
    contexto: str = "",
    historial: list[dict] | None = None,
    notas: str = "",
    resultados: list[dict] | None = None,
    correcciones: list[dict] | None = None,
    informe: str = "",
) -> list[dict]:
    """Arma la lista de mensajes para el modelo de lenguaje.

    `notas` son las anotaciones del analista (contexto biográfico, correcciones
    de transcripción, encuadre). Se pasan en un bloque aparte y explícitamente
    marcado como ajeno al discurso, para que el modelo no las cite como
    frases del sujeto.
    """
    skill = leer_skill()
    sistema = CABECERA
    if skill:
        sistema += "\n\n=== SKILL.md (instrucciones del Sistema MDS) ===\n\n" + skill
    sistema += "\n\n" + _bloque_contexto(contexto)

    modo = (modo or "A").upper()
    if modo == "C":
        sistema += (
            "\n\n=== MODO C: DIÁLOGO SOBRE EL ANÁLISIS ===\n"
            "Estás en un diálogo con quien leyó el informe MDS de un caso. Tu "
            "respuesta CONTINÚA ese análisis: no lo repitas, no lo resumas y no "
            "hagas un informe nuevo.\n"
            "- Respondé en función de lo que el informe ya estableció y de lo que "
            "la pregunta apunta.\n"
            "- FUNDAMENTÁ en los FRAGMENTOS ENTREGADOS: citá el literal con su "
            "número, así [6: \"texto literal\"]. Si el corpus no alcanza para "
            "responder algo, decilo y seguí con lo que sí está fundamentado.\n"
            "- Si la pregunta pide profundizar un punto, desarrollá el "
            "razonamiento con el texto del Lacan, no con teoría genérica.\n"
            "- 2 a 6 párrafos. Sin tablas. Sin títulos de fase."
        )
        bloques = [
            "INFORME MDS DEL CASO (leelo: es el punto de partida del diálogo):\n"
            "<informe>\n"
            f"{(informe or '').strip()}\n"
            "</informe>"
        ]
        bloques.append(f"PREGUNTA:\n{pregunta.strip()}")
        usuario = "\n\n".join(bloques)
        mensajes: list[dict] = [{"role": "system", "content": sistema}]
        for turno in (historial or [])[-6:]:
            rol = turno.get("role")
            contenido = turno.get("content", "")
            if rol in ("user", "assistant") and contenido:
                mensajes.append({"role": rol, "content": contenido})
        mensajes.append({"role": "user", "content": usuario})
        return mensajes

    if modo == "B":
        sistema += (
            "\n\n=== MODO B: INFORME MDS (4 fases) ===\n"
            "Aplicá el protocolo formal de 4 fases sobre la transcripción "
            "proporcionada, respetando la estructura de fases del SKILL.md.\n"
            "Las NOTAS DEL ANALISTA son contexto externo: pueden orientar la "
            "lectura, pero NO son discurso del sujeto. No las cites como frases "
            "textuales ni las atribuyas a quien habla."
        )
        bloques = [
            "TRANSCRIPCIÓN A ANALIZAR:\n"
            "<transcripcion>\n"
            f"{transcripcion.strip()}\n"
            "</transcripcion>"
        ]
        if notas.strip():
            bloques.append(
                "NOTAS DEL ANALISTA (contexto externo; NO forman parte del discurso "
                "del sujeto: orientan la lectura pero no son frases suyas ni se citan "
                "como tales):\n"
                "<notas>\n"
                f"{notas.strip()}\n"
                "</notas>"
            )
        bloque_corr = corrector_transcripcion.bloque_correcciones(correcciones or [])
        if bloque_corr:
            bloques.append(bloque_corr)
        # El analisis lexico se hace SOLO sobre el discurso del sujeto: las
        # anotaciones del analista no son significantes suyos.
        discurso_sujeto, _ = corrector_transcripcion.separar_notas(transcripcion)
        bloques.append(
            "DATOS LEXICOS DEL DISCURSO (conteos exactos calculados por el "
            "sistema; no los estimes, usalos tal cual):\n"
            "<datos_lexicos>\n"
            f"{analisis_lexico.analizar(discurso_sujeto)}\n"
            "</datos_lexicos>"
        )
        bloques.append(
            "MAPA DE FRAGMENTOS (concepto lacaniano <-> fragmento <-> frase "
            "literal del corpus; usalo para la tabla 3.3 y para citar):\n"
            "<mapa_fragmentos>\n"
            f"{mapa_fragmentos.armar(resultados or [])}\n"
            "</mapa_fragmentos>"
        )
        bloques.append(FORMATO_SALIDA)
        bloques.append(
            f"PEDIDO DEL USUARIO:\n{pregunta.strip() or 'Aplicá el informe MDS.'}"
        )
        usuario = "\n\n".join(bloques)
    else:
        sistema += (
            "\n\n=== MODO A: CONSULTA TEÓRICA / LECTURA CLÍNICA ===\n"
            "No uses la plantilla de 4 fases. Respondé en apartados claros, con "
            "rigor psicoanalítico, fundamentando cada afirmación en las fuentes."
        )
        usuario = pregunta.strip()

    mensajes: list[dict] = [{"role": "system", "content": sistema}]
    for turno in (historial or [])[-6:]:
        rol = turno.get("role")
        contenido = turno.get("content", "")
        if rol in ("user", "assistant") and contenido:
            mensajes.append({"role": rol, "content": contenido})
    mensajes.append({"role": "user", "content": usuario})
    return mensajes
