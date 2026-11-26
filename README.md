# Sistema MDS — RAG local del corpus lacaniano

Base de conocimiento con **RAG 100 % local** sobre un corpus de Lacan (Escritos
1-2, Seminarios 3 y 5). Los `.md` se indexan en tu propia máquina y a cada
pregunta el sistema recupera los fragmentos relevantes y le manda **solo eso**
al modelo de lenguaje.

**Cero tokens de pago · cero internet · 0 datos que salen del equipo.**

```
   base-conocimiento/*.md
            │
            │  troceado por jerarquía de títulos (H2 = capítulo, H3 = sección)
            ▼
      ┌───────────┐   qwen3-embedding:0.6b   ┌──────────────┐
      │  chunker  │ ────────────────────────► │ 1023 fragm.  │
      └───────────┘                           │  + embeddings │
                                             └──────┬───────┘
                                                    │
   pregunta ──► ┌──────────────┐  BM25 + coseno ────┤
                │  recuperación │ ◄───────────────────┘
                └──────┬───────┘
                       │  4-6 fragmentos con su procedencia
                       ▼
              ┌──────────────────┐   SKILL.md (protocolo MDS)
              │  armado prompt   │ ─────────────────────────────┐
              └────────┬─────────┘                              │
                       ▼                                        ▼
              ┌──────────────────┐              ┌──────────────────────┐
              │  Ollama local    │ ───────────► │ informe MDS / consulta│
              │ qwen2.5 · gemma3 │              │ con citas [1] [2]... │
              └──────────────────┘              └──────────────────────┘
```

## Estructura

| Ruta | Qué hay |
|---|---|
| `SKILL.md` | instrucciones del protocolo MDS (Modo A teórico / Modo B informe de 4 fases) |
| `base-conocimiento/` | **fuente de verdad**: los `.md` que se indexan |
| `rag/` | motor RAG en Python, sin dependencias externas (solo `numpy`) |
| `rag/mds_rag/` | `chunker` · `embeddings` · `store` · `retrieval` · `llm` · `prompt` · `server` + la **capa determinista** (abajo) |
| `web/` | interfaz React + Vite + Tailwind v4 (chat, buscador, biblioteca) |
| `INICIAR.cmd` | doble clic: levanta el motor y abre el navegador |
| `INICIAR-RED.cmd` | doble clic: además te da la URL para usar el celu en la misma wifi |
| `DETENER.cmd` | doble clic: frena el motor |

## Puesta en marcha

```powershell
# 1) modelo de embeddings (una vez)
ollama pull qwen3-embedding:0.6b

# 2) con doble clic
.\INICIAR.cmd          # levanta todo y abre http://127.0.0.1:8765
.\DETENER.cmd          # para frenarlo
```

O a mano, para desarrollar:

```powershell
cd rag
python cli.py indexar      # indexa el corpus (~36 s la primera vez)
python cli.py servir       # http://127.0.0.1:8765

cd ..\web                   # otra terminal
npm install
npm run dev                 # http://localhost:5173
```

Detalle completo de opciones, API y troubleshooting: **[rag/README.md](rag/README.md)**.

## El informe MDS no es un resumen

El informe es una **re-elaboración**: extrae el núcleo del malestar, lo coteja
con la teoría del corpus y de ese cotejo sale una hipótesis sobre la posición
del sujeto y sobre el trabajo clínico. Por eso el protocolo tiene tres pasos
que no son descriptivos:

- **1.3 Núcleo del Malestar** — qué se le descuadra al sujeto, en su lenguaje.
- **3.3 Cotejo con la Teoría** — qué concepto lacaniano de las fuentes
  corresponde al núcleo y **cómo ese concepto reescribe** lo que el sujeto
  dice. Una cita que no cambia la lectura es decorativa.
- **4.3 Orientación a la Cura** — qué hay que escuchar, qué ofrece el síntoma,
  qué conviene no hacer, qué pregunta abriría la cura.

Dos reglas de fidelidad que se calibraron contra informes defectuosos: la
**corrección de transcripción se aplica antes de analizar** (una frase errónea
del reconocimiento automático no es un lapsus del sujeto) y **no se fuerza la
homofonía** (si la palabra no tiene homófono real, se trabaja la polisemia del
propio hablante).

## Cuántas fuentes se recuperan (y cuántas cita el informe)

En modo B se recuperan **16 fragmentos** (`MDS_TOP_K_B`), y el prompt exige que
la tabla 3.3 tenga **una fila por fragmento**: el informe fundamenta en todo el
material recuperado, no en cuatro fuentes. Antes eran 10 fragmentos y el modelo
se quedaba con los 4 más obvios — un fallo de configuración, no del modelo.

Medido sobre el caso real (42 años, diferencia de edad), mismo prompt:

| Motor | Tiempo | Largo | Fuentes citadas | Citas literales verificadas |
|---|---|---|---|---|
| Local `qwen3:30b-a3b` (18 GB, MoE), 10 fragmentos | 6,3 min | 9.782–12.000 chars | 6 de 10 | 4–8 |
| Local `qwen3:30b-a3b`, 16 fragmentos | > 10 min | — | — | — |
| Nube `baidu/ernie-5.5-flash-preview:free` (gratis), 16 fragmentos | **1,3 min** | 17.836 chars | **16 de 16** | 19 |
| Nube `nvidia/nemotron-3-ultra-550b-a55b:free` (gratis), 10 fragmentos | 4,8 min | 16.982 chars | 9 | 8 |

O sea: en local, con 16 fragmentos el prompt crece a ~17k tokens y el modelo
parcializado en RAM se va de los 20 minutos; la nube resuelve el problema de
la exhaustividad en 1,3 minutos. Si el presupuesto es 20 min y querés 16
fuentes, la nube gratis gana.

En la cuota gratuita de OpenRouter hay dos modelos chinos: **ERNIE 5.5 Flash**
(Baidu) e **InclusionAI Ling 3.2 Flash** (Moonshot). DeepSeek, MiniMax, GLM y
Kimi existen pero **solo de pago** (y son baratísimos: DeepSeek V4 Flash
cuesta 3,6 centavos por millón de tokens). Localmente, DeepSeek y MiniMax no
entran en 32 GB.

Por defecto el motor **no manda nada a la red** (`MDS_MODO_B_NUBE=local`). Para
usar ERNIE:

```powershell
$env:MDS_MODO_B_NUBE = 'auto'   # nube gratis y, si falla, cae al local
```

## La capa determinista: lo que el modelo no tiene que adivinar

Un modelo local de 12B no tiene el rigor de uno de nube. Pero casi todo lo que
hace que un informe MDS sea **impecable** no es interpretación: es conteo,
trazabilidad y formato. Eso se calcula antes y después de que el modelo escriba,
con código:

| Módulo | Qué resuelve | Por qué importa |
|---|---|---|
| `corrector_transcripcion.py` | detecta la corrección del analista (`"se me cayó una piga"` → `"una piba me empezó a cargar"`) y la **aplica al discurso** antes del prompt | la forma errónea del aparato de registro deja de ser un significante del sujeto; el modelo ya no la puede analizar |
| `analisis_lexico.py` | cuenta repeticiones, vacilaciones, cortes y dudas; arma la **lista LA RED** con el conteo exacto de cada significante | el paso 2.3 escribe conteos calculados, no estimados |
| `mapa_fragmentos.py` | resuelve **concepto lacaniano → fragmento → frase literal** por concordancia sobre el corpus | la tabla 3.3 se arma copiando el fragmento y su cita, no adivinando |
| `verificador_citas.py` | comprueba que cada cita `[n: "…"]` exista **literalmente** en el corpus; si está en otro fragmento la reatribuye, y si está deformada la repara con el texto real | un informe MDS miente si parafrasea una fuente y la presenta como cita |

Resultado: el modelo local escribe la parte que es realmente suya (la lectura
del sujeto) y el sistema garantiza la parte verificable (conteos, fragmentos,
literales, formato). Es lo que permite que un informe local se parezca al de
nube sin pagar un solo token.

## El informe abre el diálogo

El informe MDS no es un punto final: bajo el informe hay un **diálogo sobre el
análisis** (modo C). El informe se pasa como contexto de la conversación y cada
pregunta se recupera del corpus otra vez, así que se pueden pedir
profundizaciones, ajustes o correcciones y seguir preguntando sobre el mismo
caso.

```
informe MDS ──► pregunta ──► recuperar fragmentos (pregunta + informe)
                              │
                              └► respuesta en función del análisis,
                                 citada: [6: "literal del corpus"]
```

Medido con el caso real: 43 s de respuesta, 22 citas, **22 verificadas
literalmente** contra el corpus. El hilo queda guardado, así que se puede
seguir preguntando sobre lo que respondió antes.

## CLI

```powershell
python cli.py indexar [--forzar]       # reindexa (incremental)
python cli.py buscar "objeto a petit"  # ranking de fragmentos, sin LLM
python cli.py preguntar "¿qué es...?"  # RAG completo por terminal
python cli.py servir
python cli.py calibrar                 # ranking de consultas de control
```

## Cómo se citan las fuentes

El troceado respeta la jerarquía del Markdown original, así que cada fragmento
sabe de dónde salió:

```
Seminario 5 > Capítulo 1.6."¡Atrás, Caballo!" > 1. El Problema del Otro en el
Paso-de-Sentido y la Subjetividad Analítica
```

Por eso las citas del informe son verificables: cada `[n]` apunta a un
fragmento real del corpus, con archivo, capítulo y sección.

## Decisiones de diseño (medidas, no supuestas)

- **Sin prefijos `query:` / `document:`** en qwen3-embedding: en español
  empeoran el ranking (6/8 con prefijo vs 8/8 sin).
- **Fusión híbrida** BM25 (0.15) + vectorial (0.85): el vector gana en consultas
  temáticas, el BM25 rescata términos literales raros (`Verneinung`,
  `Verdrängung`, `petit a`).
- **La sección `## Índice` se excluye** del índice: es un listado de capítulos
  y solo agrega ruido.
- **En Modo B la búsqueda se guia por la pregunta + las notas del analista**:
  recupera mejor que la pregunta sola.
- **Modelo por modo**: `qwen2.5:latest` (rápido) para consultas,
  `gemma3:12b` (más fino, ~6× más lento) para el informe MDS de 4 fases.

## Aviso

El corpus de `base-conocimiento/` contiene extracts y citas textuales de las
traducciones en español de las obras de Lacan (Paidós), que están bajo
derecho de autor. Si vas a distribuir este repositorio, conviene revisarlo o
mantenerlo privado.
