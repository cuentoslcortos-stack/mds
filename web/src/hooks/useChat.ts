import { useCallback, useEffect, useRef, useState } from 'react'
import { chatStream } from '../api'
import type { Fuente, MensajeHistorial, Modo } from '../types'

export type Etapa = 'buscando' | 'redactando' | null

export interface EstadoChat {
  cargando: boolean
  etapa: Etapa
  respuesta: string
  fuentes: Fuente[]
  error: string | null
  modelo: string | null
  backend: string | null
  terminado: boolean
}

export interface ResultadoEnvio {
  respuesta: string
  fuentes: Fuente[]
}

const INICIAL: EstadoChat = {
  cargando: false,
  etapa: null,
  respuesta: '',
  fuentes: [],
  error: null,
  modelo: null,
  backend: null,
  terminado: false,
}

interface Guardado {
  respuesta: string
  fuentes: Fuente[]
  modelo: string | null
  backend: string | null
  terminado: boolean
}

function cargar(clave: string): EstadoChat {
  try {
    const crudo = window.sessionStorage.getItem(clave)
    if (!crudo) return INICIAL
    const guardado = JSON.parse(crudo) as Partial<Guardado>
    return {
      ...INICIAL,
      respuesta: typeof guardado.respuesta === 'string' ? guardado.respuesta : '',
      fuentes: Array.isArray(guardado.fuentes) ? guardado.fuentes : [],
      modelo: guardado.modelo ?? null,
      backend: guardado.backend ?? null,
      terminado: Boolean(guardado.terminado),
    }
  } catch {
    return INICIAL
  }
}

/**
 * Estado de una consulta en streaming: va acumulando deltas y las fuentes que
 * el backend va emitiendo. La respuesta se persiste en sessionStorage para
 * que no se pierda al cambiar de vista ni al recargar la pagina.
 */
export function useChat(clave = 'mds-chat') {
  const [estado, setEstado] = useState<EstadoChat>(() => cargar(clave))
  const abortRef = useRef<AbortController | null>(null)
  const ultimo = useRef<Guardado>({
    respuesta: '',
    fuentes: [],
    modelo: null,
    backend: null,
    terminado: false,
  })

  const guardar = useCallback(
    (datos: Guardado) => {
      try {
        window.sessionStorage.setItem(clave, JSON.stringify(datos))
      } catch {
        // sin espacio en sessionStorage: se sigue en memoria
      }
    },
    [clave],
  )

  useEffect(() => {
    ultimo.current = {
      respuesta: estado.respuesta,
      fuentes: estado.fuentes,
      modelo: estado.modelo,
      backend: estado.backend,
      terminado: estado.terminado,
    }
  })

  // Escritura diferida: durante el streaming se escribe una sola vez al
  // terminar, no en cada token.
  useEffect(() => {
    if (!estado.respuesta) return
    const temporizador = window.setTimeout(() => guardar(ultimo.current), 500)
    return () => window.clearTimeout(temporizador)
  }, [estado.respuesta, guardar])

  // Si el componente se desmonta con una respuesta en curso, se guarda igual.
  useEffect(
    () => () => {
      if (ultimo.current.respuesta) guardar(ultimo.current)
    },
    [guardar],
  )

  const reiniciar = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setEstado(INICIAL)
    try {
      window.sessionStorage.removeItem(clave)
    } catch {
      // sin efecto
    }
  }, [clave])

  const enviar = useCallback(
    async (params: {
      modo: Modo
      pregunta: string
      transcripcion?: string
      notas?: string
      informe?: string
      k?: number
      historial?: MensajeHistorial[]
    }): Promise<ResultadoEnvio | null> => {
      abortRef.current?.abort()
      const control = new AbortController()
      abortRef.current = control

      setEstado({ ...INICIAL, cargando: true, etapa: 'buscando' })

      let acumulado = ''
      const fuentesLocales: Fuente[] = []

      try {
        for await (const evento of chatStream({ ...params, signal: control.signal })) {
          if (evento.tipo === 'delta') {
            const trozo = evento.texto ?? evento.delta ?? ''
            acumulado += trozo
            setEstado((prev) => ({ ...prev, etapa: 'redactando', respuesta: acumulado }))
          } else if (evento.tipo === 'fuente') {
            fuentesLocales.push(evento.fuente)
            setEstado((prev) => ({ ...prev, fuentes: [...fuentesLocales] }))
          } else {
            if (evento.respuesta) acumulado = evento.respuesta
            if (evento.fuentes?.length) {
              fuentesLocales.length = 0
              fuentesLocales.push(...evento.fuentes)
            }
            setEstado((prev) => ({
              ...prev,
              respuesta: acumulado,
              fuentes: [...fuentesLocales],
              modelo: evento.modelo ?? prev.modelo,
              backend: evento.backend ?? prev.backend,
            }))
          }
        }

        setEstado((prev) => ({ ...prev, cargando: false, etapa: null, terminado: true }))
        return { respuesta: acumulado, fuentes: [...fuentesLocales] }
      } catch (error) {
        if (control.signal.aborted) {
          setEstado((prev) => ({ ...prev, cargando: false, etapa: null }))
          return null
        }
        setEstado((prev) => ({
          ...prev,
          cargando: false,
          etapa: null,
          error: error instanceof Error ? error.message : 'Error inesperado.',
        }))
        return null
      }
    },
    [],
  )

  return { estado, enviar, reiniciar }
}
