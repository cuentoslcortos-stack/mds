/** Tipos del contrato de API del motor RAG (fijo, no se inventa). */

export interface Health {
  ok: boolean
  ollama: boolean
  embed_model: string
  llm_model: string
  llm_model_b?: string
  backend: string
  nube?: {
    modelo: string
    gratis_verificado: boolean
    politica: 'local' | 'auto' | 'nube' | string
    solo_gratis: boolean
    key_encontrada: boolean
  }
  indice?: {
    chunks: number
    documentos: number
    actualizado: string
  }
}

export interface DocumentoInfo {
  archivo: string
  documento: string
  chunks: number
  palabras: number
  hash: string
  actualizado: string
}

export interface Fragmento {
  id: string
  archivo: string
  documento: string
  capitulo: string
  seccion: string
  titulo: string
  score: number
  texto: string
  palabras: number
}

export interface Fuente {
  archivo: string
  documento: string
  capitulo: string
  seccion: string
  titulo: string
  score: number
  extracto: string
  palabras: number
}

export interface ResultadoBusqueda {
  consulta: string
  resultados: Fragmento[]
}

export interface ReindexResult {
  ok: boolean
  procesados: string[]
  chunks: number
  duracion_s?: number
  sin_cambios: boolean
}

export type Modo = 'A' | 'B' | 'C'

export interface MensajeHistorial {
  role: 'user' | 'assistant'
  content: string
}

/** Eventos NDJSON que emite POST /api/chat con stream:true. */
export type EventoStream =
  | { tipo: 'delta'; texto: string; delta?: string }
  | { tipo: 'fuente'; fuente: Fuente }
  | {
      tipo: 'fin'
      respuesta: string
      fuentes: Fuente[]
      modelo: string
      backend: string
    }
