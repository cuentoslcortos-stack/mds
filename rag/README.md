# Sistema MDS — Motor RAG local (Lacan)

Base de conocimiento con **RAG 100 % local**: los `.md` de `base-conocimiento/` se
indexan en tu máquina y a cada pregunta el sistema busca los 3-6 fragmentos
relevantes y le manda **solo eso** al modelo de lenguaje. Cero tokens de pago,
cero internet, 0 datos que salgan de la máquina.

```
Sistema/
├── SKILL.md                  # instrucciones del protocolo MDS (Modo A / Modo B)
├── base-conocimiento/        # FUENTE DE VERDAD: los .md que se indexan
├── rag/                      # motor RAG (Python, sin dependencias externas)
│   ├── cli.py                # indexar / buscar / preguntar / servir / calibrar
│   └── mds_rag/              # chunker, embeddings, store, retrieval, llm, prompt, server
└── web/                      # interfaz React + Vite + Tailwind v4
```

## Requisitos

- **Ollama** corriendo en `127.0.0.1:11434`
  - embeddings: `ollama pull qwen3-embedding:0.6b`
  - modelo de lenguaje: `qwen2.5:latest` (4,7 GB) o `gemma3:12b` (8,2 GB)
- **Python 3.11+** con `numpy` (ya está en esta máquina)
- **Node 20+** para la interfaz web

## Puesta en marcha

### Con doble clic (lo normal)

| Archivo | Qué hace |
|---|---|
| `INICIAR.cmd` | levanta el motor y abre `http://127.0.0.1:8765` en el navegador |
| `INICIAR-RED.cmd` | lo mismo, pero además te muestra la URL para usar el **celu** en la misma wifi |
| `DETENER.cmd` | frena el motor |

`INICIAR.cmd` se ocupa de todo: verifica que Ollama esté respondiendo (y lo
levanta si no), compila la interfaz web la primera vez, levanta el backend,
espera a que esté listo y abre el navegador. Si el motor ya estaba corriendo,
solo abre el navegador.

### Manual (para desarrollar)

Dos terminales.

**1) Backend (API + motor)**

```powershell
cd F:\Carreras\Psicologia\Verrua_Terapias_GEM\MDS_OPT\Sistema\rag
python cli.py indexar        # sólo la primera vez (o al cambiar el corpus)
python cli.py servir         # http://127.0.0.1:8765
```

**2) Interfaz web**

```powershell
cd F:\Carreras\Psicologia\Verrua_Terapias_GEM\MDS_OPT\Sistema\web
npm install                  # sólo la primera vez
npm run dev                  # http://localhost:5173
```

La web habla con el backend por el proxy de Vite (`/api` → `127.0.0.1:8765`),
así que no hay CORS ni que configurar nada.

> Si preferís una sola app servida por el backend: `npm run build` en `web/` y
> el servidor Python sirve `web/dist` en el mismo puerto 8765.

### ¿Desde el celu o desde internet?

El motor es **local por diseño**: el modelo de lenguaje corre en tu GPU y el
corpus nunca sale de la máquina.

- **Desde el celu, en la misma wifi**: sí, con `INICIAR-RED.cmd`. Te imprime
  la URL del tipo `http://192.168.x.x:8765`. La interfaz y el corpus siguen
  estando en tu compu; el celu es solo otro navegador.
- **Desde internet (fuera de casa)**: se puede exponiendo el puerto con un
  túnel (cloudflared / ngrok). El túnel solo reenvía la UI: el LLM y el corpus
  siguen corriendo en tu equipo. Ojo: cualquiera con la URL podría consultarle
  tu corpus, así que si lo exponés, poné una contraseña delante.
- **GitHub Pages**: sirve la interfaz estática, pero no sirve para esto: la
  interfaz necesita hablar con un backend, y el backend necesita tu GPU.

## CLI

```powershell
python cli.py indexar [--forzar]        # construye/actualiza el índice
python cli.py buscar "objeto a petit"    # ranking de fragmentos, sin LLM
python cli.py preguntar "¿qué es...?"    # RAG completo por terminal
python cli.py preguntar "..." --modo B --transcripcion caso.txt
python cli.py servir [--puerto 8765]
python cli.py calibrar                   # ranking de consultas de control
```

## Agregar material al corpus

1. Poné el `.md` nuevo en `base-conocimiento/`.
2. En la web: **Biblioteca → Reindexar**. O en terminal: `python cli.py indexar`.

El reindexado es **incremental**: solo se re-embeben los archivos nuevos o
modificados; los que no cambiaron se reutilizan del caché. Si el corpus no
cambió, responde en ~0,5 s. Si **borrás** un `.md`, el índice lo retira
automáticamente.

Cada fragmento conserva su procedencia (`documento > capítulo > sección`), así
que las citas siempre dicen de dónde salieron.

## El informe MDS (Modo B) no es un resumen

Es lo más importante del sistema, y lo que más se calibró. Un informe que se
limita a describir lo que el sujeto dijo no sirve: el informe es una
**re-elaboración** que extrae el núcleo del malestar, lo coteja con la teoría
del corpus y de ahí sale una hipótesis sobre la posición del sujeto y sobre el
trabajo clínico.

Por eso el protocolo tiene tres pasos que antes no tenía:

| Paso | Qué hace |
|---|---|
| **1.3 Núcleo del Malestar** | qué se le descuadra al sujeto, en su propio lenguaje, sostenido con sus fragmentos literales |
| **3.3 Cotejo con la Teoría** | qué concepto lacaniano de las fuentes corresponde al núcleo, y **cómo ese concepto reescribe** lo que el sujeto dice |
| **4.3 Orientación a la Cura** | qué hay que escuchar, qué ofrece el síntoma, qué conviene no hacer, qué pregunta abriría la cura |

Además, dos reglas de fidelidad que se agregaron después de ver informes
defectuosos:

- **La corrección de transcripción se aplica antes de analizar.** Una frase
  errónea del reconocimiento automático es un hecho del aparato de registro,
  **no un lapsus del sujeto**: no puede ser el significante nodal ni entrar en
  la Red. Por eso el material va en dos campos: el discurso del sujeto (1) y
  las notas del analista con las correcciones y el contexto (2). Si las pegás
  todo junto, el informe las separa igual, pero es mejor separadas.
- **No se fuerza la homofonía.** Si la palabra no tiene homófono real, el
  informe lo dice y trabaja la **polisemia del propio hablante**: los
  sentidos distintos que le da a una misma expresión y las inversiones de
  sentido entre dos apariciones de la misma palabra.

### Qué modelo usar

| Modo | Modelo | Tiempo | Para qué |
|---|---|---|---|
| A — consulta teórica | `qwen2.5:latest` (4,7 GB) | ~30 s | consultas rápidas |
| B — informe MDS | `gemma3:12b` (8,2 GB) | ~2,5 min | el informe de 4 fases |

Medido sobre un caso real: `qwen2.5:7b` **inventa homófonos** y no llega a
una orientación clínica; `gemma3:12b` aísla el significante nodal correcto,
valida la Red y llega a la 4.3. La diferencia no es de estilo: es de fidelidad
al protocolo.

Si querés más profundidad todavía, hay un motor de nube **gratis** disponible
como opción (no viene activado):

```powershell
$env:MDS_MODO_B_NUBE = "auto"   # nube gratis primero, con caída al local
```

- Los modelos son los `:free` de OpenRouter (cuota gratuita propia, **sin
  saldo y sin tarjeta**). El más grande disponible es un Nemotron Ultra 550B.
- **Traba de costo**: con `MDS_SOLO_GRATIS=1` (default) el motor se niega a
  llamar a cualquier modelo que no sea `:free` con precio 0/0 verificado en el
  catálogo. Si la cuota gratuita se agota, devuelve 429 y el motor cae al
  modelo local; nunca cobra del saldo.
- La **indexación y la búsqueda siguen siendo locales** (Ollama en tu equipo).
  Solo sale del equipo el prompt con los fragmentos recuperados, si activás
  esta opción.
- `GET /api/modelos` te lista los gratuitos verificados y cuál es la política
  vigente.

Por defecto está todo local: nada sale de la máquina.

## Configuración (variables de entorno)

| Variable | Default | Qué hace |
|---|---|---|
| `MDS_EMBED_MODEL` | `qwen3-embedding:0.6b` | modelo de embeddings |
| `MDS_LLM_MODEL` | `qwen2.5:latest` | modelo de lenguaje |
| `MDS_LLM_BACKEND` | `ollama` | `ollama` o `openrouter` |
| `MDS_NUM_CTX` | `16384` | ventana de contexto |
| `MDS_TEMPERATURA` | `0.3` | temperatura de muestreo |
| `MDS_TOP_K` | `4` | fragmentos recuperados (Modo A) |
| `MDS_TOP_K_B` | `6` | fragmentos recuperados (Modo B / informe MDS) |
| `MDS_PESO_VECTOR` | `0.85` | peso del ranking vectorial en la fusión |
| `MDS_PESO_LEXICO` | `0.15` | peso de BM25 en la fusión |
| `MDS_RAG_PORT` | `8765` | puerto del backend |
| `MDS_RAG_STORAGE` | `rag/storage` | dónde vive el índice |

Para usar un modelo de OpenRouter (`:free`, consume internet pero no plata):

```powershell
$env:MDS_LLM_BACKEND = "openrouter"
$env:OPENROUTER_API_KEY = "sk-or-v1-..."
$env:MDS_OPENROUTER_MODEL = "deepseek/deepseek-chat-v3-0324:free"
```

## API

| Endpoint | Body | Devuelve |
|---|---|---|
| `GET /api/health` | — | estado de Ollama, modelos, tamaño del índice |
| `GET /api/documentos` | — | documentos indexados con chunks y palabras |
| `POST /api/buscar` | `{consulta, k}` | ranking de fragmentos con score |
| `POST /api/chat` | `{pregunta, modo, transcripcion, notas, k, historial, stream}` | respuesta (NDJSON si `stream:true`) |
| `POST /api/reindex` | `{forzar?}` | reindexa el corpus |

**Modo A** = consulta teórica libre. **Modo B** = informe MDS en 4 fases, exige
`transcripcion`.

`notas` son las anotaciones del analista (contexto biográfico, correcciones de
transcripción, encuadre). Van en un bloque aparte, marcado como ajeno al
discurso, para que el modelo las use para leer sin citarlas como frases del
sujeto.

Eventos del stream (`stream:true`), uno por línea:

```json
{"tipo":"fuente","fuente":{...}}   // uno por fragmento recuperado
{"tipo":"delta","texto":"..."}      // pedacito de la respuesta
{"tipo":"fin","respuesta":"...","fuentes":[...],"modelo":"...","backend":"..."}
```

## Calibración (por qué está configurado así)

Medido sobre 16 consultas de control + 10 de términos raros:

- **Prefijos `query:` / `document:` de qwen3-embedding: EMPEORAN** el ranking en
  español (6/8 con prefijo vs 8/8 sin). Se indexa y se consulta simétricamente,
  sin prefijo.
- **Híbrido (BM25 0.15 + vector 0.85)** le gana al vector puro en términos
  raros (6/10 vs 5/10) y empata en los temáticos.
- En **Modo B la búsqueda se guia por la pregunta + las notas del analista**:
  recupera mejor que la pregunta sola o que pregunta+notas+discurso completo.
- El chunker **excluye la sección `## Índice`** (es un listado de capítulos: solo
  agrega ruido) y respeta la jerarquía `H2 = capítulo`, `H3+ = sección`.

Si cambiás el modelo de embeddings o los prefijos, el caché se invalida solo
(la firma del embedding viaja dentro del archivo de caché).

## Problemas frecuentes

**`404: model 'X' not found`** → el modelo no está instalado con ese tag. El
servidor lo resuelve solo (cae a `qwen2.5:latest` o al primero disponible), pero
si querés uno puntual: `ollama pull <modelo>`.

**`No se pudo contactar al motor RAG`** → el backend no está levantado
(`python cli.py servir`) o la web está en otro puerto.

**El índice dice 0 chunks** → `python cli.py indexar`.

**La respuesta tarda** → el modelo local genera en tu GPU. `qwen2.5:latest` es
el más rápido; `gemma3:12b` es más fino pero se va de VRAM (8,2 GB) y va más
lento por offload a RAM.
