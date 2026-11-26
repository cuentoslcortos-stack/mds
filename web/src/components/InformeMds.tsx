import { type FormEvent } from 'react'
import { useChat } from '../hooks/useChat'
import { usePersistente } from '../hooks/usePersistente'
import { Markdown } from './Markdown'
import { Fuentes } from './Fuentes'
import { Aviso, BotonCopiar, EstadoVacio, Spinner } from './Piezas'
import type { MensajeHistorial } from '../types'

export default function InformeMds() {
  const [transcripcion, setTranscripcion] = usePersistente<string>(
    'mds-informe-transcripcion',
    '',
  )
  const [notas, setNotas] = usePersistente<string>('mds-informe-notas', '')
  const [pregunta, setPregunta] = usePersistente<string>('mds-informe-pregunta', '')
  const [historial, setHistorial] = usePersistente<MensajeHistorial[]>(
    'mds-historial-informe',
    [],
  )
  const { estado, enviar } = useChat('mds-chat-informe')
  // Dialogo sobre el analisis: el informe es el contexto de la conversacion.
  const [preguntaDialogo, setPreguntaDialogo] = usePersistente<string>(
    'mds-dialogo-pregunta',
    '',
  )
  const [historialDialogo, setHistorialDialogo] = usePersistente<MensajeHistorial[]>(
    'mds-dialogo-historial',
    [],
  )
  const dialogo = useChat('mds-chat-dialogo')

  const generar = async (evento: FormEvent) => {
    evento.preventDefault()
    if (estado.cargando) return
    const consulta = pregunta.trim()
    const texto = transcripcion.trim()
    if (!consulta && !texto) return

    setPregunta('')
    const resultado = await enviar({
      modo: 'B',
      pregunta: consulta || 'Aplicá el protocolo MDS a la transcripción proporcionada.',
      transcripcion: texto,
      notas: notas.trim(),
      k: 4,
      historial,
    })
    if (resultado?.respuesta) {
      setHistorial((prev) => [
        ...prev,
        { role: 'user', content: consulta || texto.slice(0, 200) },
        { role: 'assistant', content: resultado.respuesta },
      ])
    }
  }

  /** Pregunta al corpus en funcion del informe recien generado. */
  const preguntar = async (evento: FormEvent) => {
    evento.preventDefault()
    if (dialogo.estado.cargando) return
    const consulta = preguntaDialogo.trim()
    const informe = estado.respuesta.trim()
    if (!consulta || !informe) return

    setPreguntaDialogo('')
    const resultado = await dialogo.enviar({
      modo: 'C',
      pregunta: consulta,
      informe,
      historial: historialDialogo,
    })
    if (resultado?.respuesta) {
      setHistorialDialogo((prev) => [
        ...prev,
        { role: 'user', content: consulta },
        { role: 'assistant', content: resultado.respuesta },
      ])
    }
  }

  return (
    <div className="space-y-6">
      <form onSubmit={generar} className="space-y-4">
        <div className="space-y-2">
          <label htmlFor="transcripcion-mds" className="block text-sm font-semibold text-app-fg">
            1 · Transcripción literal del discurso
          </label>
          <textarea
            id="transcripcion-mds"
            value={transcripcion}
            onChange={(e) => setTranscripcion(e.target.value)}
            rows={9}
            placeholder="Pegá acá SOLO lo que dice el sujeto, textual…"
            className="w-full resize-y rounded-lg border border-app-border bg-app-surface px-4 py-3 font-serif text-app-fg placeholder:font-sans placeholder:text-app-muted focus:border-app-accent"
          />
          <p className="text-xs text-app-muted">
            Solo el discurso del sujeto. Las correcciones de transcripción y el contexto van en el
            campo 2: si van pegados acá, el informe puede tomarlos como palabras suyas.
          </p>
        </div>

        <div className="space-y-2">
          <label htmlFor="notas-mds" className="block text-sm font-semibold text-app-fg">
            2 · Notas del analista (correcciones de transcripción y contexto)
          </label>
          <textarea
            id="notas-mds"
            value={notas}
            onChange={(e) => setNotas(e.target.value)}
            rows={4}
            placeholder="Ej.: el automático transcribió 'se me cayó una piga'; en realidad dijo 'una piba me empezó a cargar'. El sujeto tiene 42 años y estudia con compañeros de 18…"
            className="w-full resize-y rounded-lg border border-app-border bg-app-surface px-4 py-3 text-app-fg placeholder:text-app-muted focus:border-app-accent"
          />
          <p className="text-xs text-app-muted">
            Contexto externo: orienta la lectura del analista, pero no forma parte del discurso
            del sujeto y no se cita como frase textual.
          </p>
        </div>

        <div className="space-y-2">
          <label htmlFor="pregunta-mds" className="block text-sm font-semibold text-app-fg">
            3 · Pregunta u observación clínica (opcional)
          </label>
          <input
            id="pregunta-mds"
            type="text"
            value={pregunta}
            onChange={(e) => setPregunta(e.target.value)}
            placeholder="Ej.: ¿qué lectura del divisa transferencia?"
            className="w-full rounded-lg border border-app-border bg-app-surface px-4 py-2.5 text-app-fg placeholder:text-app-muted focus:border-app-accent"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="submit"
            disabled={estado.cargando || (!pregunta.trim() && !transcripcion.trim())}
            className="inline-flex items-center gap-2 rounded-md bg-app-accent px-4 py-2 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {estado.cargando ? <Spinner className="border-white/40 border-t-white" /> : null}
            {estado.cargando ? 'Generando informe…' : 'Generar informe MDS'}
          </button>
          <p className="text-xs text-app-muted">
            Modo B · protocolo formal en 4 fases: Escucha Activa, Deconstrucción, Articulación y Síntesis.
          </p>
        </div>
      </form>

      {estado.error && <Aviso titulo="No se pudo completar el informe">{estado.error}</Aviso>}

      {estado.cargando && !estado.respuesta && (
        <div className="flex items-center gap-3 rounded-lg border border-app-border bg-app-surface px-4 py-3 text-sm text-app-muted">
          <Spinner />
          <span>buscando en el corpus…</span>
        </div>
      )}

      {!estado.respuesta && !estado.cargando && !estado.error && (
        <EstadoVacio titulo="Todavía no hay informe">
          <p>
            El protocolo MDS recorre cuatro fases: <em>La Escucha Activa</em> (aislar el
            fallido o equívoco), <em>La Deconstrucción</em> (análisis fonético y homófono),
            <em>La Articulación</em> (sustitución y demanda del Otro) y <em>La Síntesis</em>
            (estructura clínica y economía del goce). Cada fase se fundamenta en el corpus
            indexado.
          </p>
        </EstadoVacio>
      )}

      {estado.respuesta && (
        <section aria-live="polite" aria-busy={estado.cargando} className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-app-border pb-2">
            <h2 className="text-sm font-semibold uppercase tracking-[0.15em] text-app-muted">
              Informe MDS
            </h2>
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
              Generado con <span className="font-mono">{estado.modelo}</span> ({estado.backend})
              fundamentado en {estado.fuentes.length} fragmento
              {estado.fuentes.length === 1 ? '' : 's'} del corpus.
            </p>
          )}

          {/* Dialogo: el informe abre la conversacion con el corpus. */}
          <section className="space-y-3 rounded-lg border border-app-border bg-app-surface px-4 py-4 sm:px-5">
            <div className="border-b border-app-border pb-2">
              <h3 className="text-sm font-semibold uppercase tracking-[0.15em] text-app-muted">
                Diálogo sobre el análisis
              </h3>
              <p className="mt-1 text-xs text-app-muted">
                Preguntale al corpus: cada respuesta se recupera del corpus y cita el
                literal del fragmento. El informe es el punto de partida de la conversación.
              </p>
            </div>

            {historialDialogo.length > 0 && (
              <div className="space-y-3">
                {historialDialogo.map((turno, i) => (
                  <div key={i} className="space-y-1">
                    {turno.role === 'user' ? (
                      <p className="text-sm font-semibold text-app-fg">
                        <span className="mr-2 text-app-muted">›</span>
                        {turno.content}
                      </p>
                    ) : (
                      <div className="rounded-md border border-app-border bg-app-raised px-3 py-2">
                        <Markdown texto={turno.content} />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {dialogo.estado.cargando && (
              <div className="flex items-center gap-2 text-xs text-app-muted">
                <Spinner />
                <span>buscando en el corpus…</span>
              </div>
            )}

            {dialogo.estado.error && (
              <Aviso titulo="No se pudo responder">{dialogo.estado.error}</Aviso>
            )}

            <form onSubmit={preguntar} className="flex flex-wrap items-end gap-2">
              <input
                type="text"
                value={preguntaDialogo}
                onChange={(e) => setPreguntaDialogo(e.target.value)}
                placeholder="Ej.: ¿qué sostiene la idea de que la envidia cambia de agente a destinatario?"
                className="min-w-[16rem] flex-1 rounded-lg border border-app-border bg-app-surface px-3 py-2.5 text-sm text-app-fg placeholder:text-app-muted focus:border-app-accent"
              />
              <button
                type="submit"
                disabled={dialogo.estado.cargando || !preguntaDialogo.trim() || !estado.respuesta}
                className="inline-flex items-center gap-2 rounded-md border border-app-accent px-4 py-2 text-sm font-semibold text-app-accent transition-colors hover:bg-app-accent-soft disabled:cursor-not-allowed disabled:opacity-50"
              >
                {dialogo.estado.cargando ? <Spinner /> : null}
                {dialogo.estado.cargando ? 'Consultando…' : 'Consultar al corpus'}
              </button>
            </form>
            {!estado.respuesta && (
              <p className="text-xs text-app-muted">
                Primero generá el informe: el diálogo parte de él.
              </p>
            )}
          </section>
        </section>
      )}

      <Fuentes fuentes={estado.fuentes} />
    </div>
  )
}
