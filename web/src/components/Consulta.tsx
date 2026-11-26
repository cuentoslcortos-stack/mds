import { useState, type FormEvent } from 'react'
import { useChat } from '../hooks/useChat'
import { usePersistente } from '../hooks/usePersistente'
import { Markdown } from './Markdown'
import { Fuentes } from './Fuentes'
import { Aviso, BotonCopiar, EstadoVacio, Spinner } from './Piezas'
import type { MensajeHistorial } from '../types'

const EJEMPLOS = [
  '¿Qué es el objeto a petit y cómo se diferencia del objeto grande?',
  'Explicame el significante(chain) y su relación con la demanda al Otro.',
  '¿Qué dice el Seminario 5 sobre la función del analista?',
]

export default function Consulta() {
  const [pregunta, setPregunta] = useState('')
  const [historial, setHistorial] = usePersistente<MensajeHistorial[]>(
    'mds-historial-consulta',
    [],
  )
  const { estado, enviar } = useChat('mds-chat-consulta')

  const consultar = async (evento: FormEvent) => {
    evento.preventDefault()
    const texto = pregunta.trim()
    if (!texto || estado.cargando) return
    setPregunta('')
    const resultado = await enviar({ modo: 'A', pregunta: texto, k: 4, historial })
    if (resultado?.respuesta) {
      setHistorial((prev) => [
        ...prev,
        { role: 'user', content: texto },
        { role: 'assistant', content: resultado.respuesta },
      ])
    }
  }

  return (
    <div className="space-y-6">
      <form onSubmit={consultar} className="space-y-3">
        <label htmlFor="pregunta-consulta" className="block text-sm font-semibold text-app-fg">
          Pregunta teórica
        </label>
        <textarea
          id="pregunta-consulta"
          value={pregunta}
          onChange={(e) => setPregunta(e.target.value)}
          rows={3}
          placeholder="Ej.: ¿cómo se articula el objeto a petit en los Escritos?"
          className="w-full resize-y rounded-lg border border-app-border bg-app-surface px-4 py-3 text-app-fg placeholder:text-app-muted focus:border-app-accent"
        />
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="submit"
            disabled={!pregunta.trim() || estado.cargando}
            className="inline-flex items-center gap-2 rounded-md bg-app-accent px-4 py-2 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {estado.cargando ? <Spinner className="border-white/40 border-t-white" /> : null}
            {estado.cargando ? 'Consultando…' : 'Consultar corpus'}
          </button>
          <p className="text-xs text-app-muted">
            Modo A · respuesta teórica abierta, fundamentada en Escritos 1-2 y Seminarios 3 y 5.
          </p>
        </div>
      </form>

      {estado.error && <Aviso titulo="No se pudo completar la consulta">{estado.error}</Aviso>}

      {estado.cargando && !estado.respuesta && (
        <div className="flex items-center gap-3 rounded-lg border border-app-border bg-app-surface px-4 py-3 text-sm text-app-muted">
          <Spinner />
          <span>buscando en el corpus…</span>
        </div>
      )}

      {!estado.respuesta && !estado.cargando && !estado.error && (
        <EstadoVacio titulo="Todavía no consultaste el corpus">
          <p>
            Escribí una pregunta teórica. El motor busca fragmentos del corpus indexado
            (Escritos 1-2, Seminarios 3 y 5) y redacta una respuesta citando de dónde
            sale cada afirmación.
          </p>
          <ul className="mt-3 space-y-1 text-left">
            {EJEMPLOS.map((ejemplo) => (
              <li key={ejemplo}>
                <button
                  type="button"
                  onClick={() => setPregunta(ejemplo)}
                  className="text-app-accent underline decoration-dotted underline-offset-4 hover:decoration-solid"
                >
                  {ejemplo}
                </button>
              </li>
            ))}
          </ul>
        </EstadoVacio>
      )}

      {estado.respuesta && (
        <section aria-live="polite" aria-busy={estado.cargando} className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-app-border pb-2">
            <h2 className="text-sm font-semibold uppercase tracking-[0.15em] text-app-muted">Respuesta</h2>
            <div className="flex items-center gap-2">
              {estado.cargando && (
                <span className="inline-flex items-center gap-2 text-xs text-app-muted">
                  <Spinner />
                  {estado.etapa === 'redactando' ? 'redactando…' : 'buscando en el corpus…'}
                </span>
              )}
              <BotonCopiar texto={estado.respuesta} />
            </div>
          </div>

          <article className="rounded-lg border border-app-border bg-app-surface px-4 py-4 sm:px-6 sm:py-5">
            <Markdown texto={estado.respuesta} cursor={estado.cargando} />
          </article>

          {estado.modelo && (
            <p className="text-xs text-app-muted">
              Generado con <span className="font-mono">{estado.modelo}</span> (
              {estado.backend}) sobre {estado.fuentes.length} fragmento
              {estado.fuentes.length === 1 ? '' : 's'} del corpus.
            </p>
          )}
        </section>
      )}

      <Fuentes fuentes={estado.fuentes} />
    </div>
  )
}
