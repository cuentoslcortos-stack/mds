import type {
  DocumentoInfo,
  EventoStream,
  Fuente,
  Health,
  MensajeHistorial,
  Modo,
  ResultadoBusqueda,
  ReindexResult,
} from './types'

/**
 * Prefijo de la API. Nunca se hardcodea la URL del backend en el código de la
 * app: el dev server (o el preview) reenvía /api -> VITE_API_TARGET.
 */
const API_BASE = import.meta.env.VITE_API_BASE ?? '/api'

export class ApiError extends Error {
  status: number

  constructor(mensaje: string, status: number) {
    super(mensaje)
    this.name = 'ApiError'
    this.status = status
  }
}

async function mensajeDeError(res: Response): Promise<string> {
  try {
    const cuerpo = (await res.json()) as { error?: unknown }
    if (typeof cuerpo?.error === 'string' && cuerpo.error.trim()) return cuerpo.error
  } catch {
    // cuerpo no JSON: cae al mensaje genérico
  }
  return `El motor RAG respondió con error ${res.status}.`
}

async function pedir<T>(ruta: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${API_BASE}${ruta}`, init)
  } catch {
    throw new ApiError(
      'No se pudo contactar al motor RAG. Revisá que el backend esté levantado.',
      0,
    )
  }
  if (!res.ok) throw new ApiError(await mensajeDeError(res), res.status)
  return (await res.json()) as T
}

export function getHealth(): Promise<Health> {
  return pedir<Health>('/health')
}

export function getDocumentos(): Promise<{ documentos: DocumentoInfo[] }> {
  return pedir<{ documentos: DocumentoInfo[] }>('/documentos')
}

export function buscar(consulta: string, k = 8): Promise<ResultadoBusqueda> {
  return pedir<ResultadoBusqueda>('/buscar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ consulta, k }),
  })
}

export function reindex(): Promise<ReindexResult> {
  return pedir<ReindexResult>('/reindex', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })
}

/**
 * Cambia el motor del informe MDS en caliente: 'local' (nada sale de la
 * maquina), 'auto' (nube gratis y, si falla, local) o 'nube'.
 */
export function setMotor(modo: string): Promise<{ ok: boolean; politica: string }> {
  return pedir<{ ok: boolean; politica: string }>('/motor', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ modo }),
  })
}

export function chatCompleto(params: {
  pregunta: string
  modo: Modo
  transcripcion?: string
  notas?: string
  informe?: string
  k?: number
  historial?: MensajeHistorial[]
}): Promise<{ respuesta: string; fuentes: Fuente[]; modelo: string; backend: string }> {
  return pedir('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...params, stream: false }),
  })
}

/**
 * POST /api/chat con stream:true → NDJSON. Devuelve un generador que emite
 * un evento por línea JSON.
 */
export async function* chatStream(params: {
  pregunta: string
  modo: Modo
  transcripcion?: string
  notas?: string
  informe?: string
  k?: number
  historial?: MensajeHistorial[]
  signal?: AbortSignal
}): AsyncGenerator<EventoStream> {
  let res: Response
  try {
    res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...params, stream: true }),
      signal: params.signal,
    })
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') return
    throw new ApiError(
      'No se pudo contactar al motor RAG. Revisá que el backend esté levantado.',
      0,
    )
  }

  if (!res.ok) throw new ApiError(await mensajeDeError(res), res.status)
  if (!res.body) throw new ApiError('El navegador no pudo abrir el stream de respuesta.', 0)

  const reader = res.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      let corte = buffer.indexOf('\n')
      while (corte !== -1) {
        const linea = buffer.slice(0, corte).trim()
        buffer = buffer.slice(corte + 1)
        if (linea) {
          try {
            yield JSON.parse(linea) as EventoStream
          } catch {
            throw new ApiError('El motor RAG devolvió una respuesta mal formada.', res.status)
          }
        }
        corte = buffer.indexOf('\n')
      }
    }

    const resto = buffer.trim()
    if (resto) {
      try {
        yield JSON.parse(resto) as EventoStream
      } catch {
        throw new ApiError('El motor RAG devolvió una respuesta mal formada.', res.status)
      }
    }
  } finally {
    reader.releaseLock()
  }
}
