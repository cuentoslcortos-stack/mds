import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { buscar, getDocumentos, reindex } from '../api'
import type { DocumentoInfo, Fragmento, ReindexResult } from '../types'
import { Aviso, Spinner } from './Piezas'

export default function Biblioteca({ alReindexar }: { alReindexar: () => void }) {
  const [documentos, setDocumentos] = useState<DocumentoInfo[]>([])
  const [cargandoDocs, setCargandoDocs] = useState(true)
  const [errorDocs, setErrorDocs] = useState<string | null>(null)

  const [reindexando, setReindexando] = useState(false)
  const [resultadoReindex, setResultadoReindex] = useState<ReindexResult | null>(null)
  const [errorReindex, setErrorReindex] = useState<string | null>(null)

  const [consulta, setConsulta] = useState('')
  const [buscando, setBuscando] = useState(false)
  const [resultados, setResultados] = useState<Fragmento[]>([])
  const [errorBusqueda, setErrorBusqueda] = useState<string | null>(null)
  const [busquedaHecha, setBusquedaHecha] = useState(false)

  const cargarDocumentos = useCallback(async () => {
    setCargandoDocs(true)
    try {
      const datos = await getDocumentos()
      setDocumentos(datos.documentos ?? [])
      setErrorDocs(null)
    } catch (error) {
      setErrorDocs(error instanceof Error ? error.message : 'Error desconocido.')
    } finally {
      setCargandoDocs(false)
    }
  }, [])

  useEffect(() => {
    void cargarDocumentos()
  }, [cargarDocumentos])

  const correrReindex = async () => {
    setReindexando(true)
    setErrorReindex(null)
    setResultadoReindex(null)
    try {
      const res = await reindex()
      setResultadoReindex(res)
      await cargarDocumentos()
      alReindexar()
    } catch (error) {
      setErrorReindex(error instanceof Error ? error.message : 'Error desconocido.')
    } finally {
      setReindexando(false)
    }
  }

  const correrBusqueda = async (evento: FormEvent) => {
    evento.preventDefault()
    const texto = consulta.trim()
    if (!texto || buscando) return
    setBuscando(true)
    setErrorBusqueda(null)
    try {
      const res = await buscar(texto, 8)
      setResultados(res.resultados ?? [])
      setBusquedaHecha(true)
    } catch (error) {
      setErrorBusqueda(error instanceof Error ? error.message : 'Error desconocido.')
      setResultados([])
    } finally {
      setBuscando(false)
    }
  }

  return (
    <div className="space-y-8">
      <section aria-labelledby="titulo-corpus" className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 id="titulo-corpus" className="text-lg font-semibold text-app-fg">
              Corpus indexado
            </h2>
            <p className="text-xs text-app-muted">
              {documentos.length} documento{documentos.length === 1 ? '' : 's'} ·{' '}
              {documentos.reduce((total, doc) => total + (doc.chunks ?? 0), 0)} chunks ·{' '}
              {documentos.reduce((total, doc) => total + (doc.palabras ?? 0), 0).toLocaleString('es-AR')}{' '}
              palabras
            </p>
          </div>

          <button
            type="button"
            onClick={() => void correrReindex()}
            disabled={reindexando}
            className="inline-flex items-center gap-2 rounded-md border border-app-border bg-app-surface px-4 py-2 text-sm font-semibold text-app-fg transition-colors hover:border-app-accent hover:text-app-accent disabled:cursor-not-allowed disabled:opacity-60"
          >
            {reindexando ? <Spinner /> : <span aria-hidden="true">⟳</span>}
            {reindexando ? 'Reindexando…' : 'Reindexar'}
          </button>
        </div>

        {errorDocs && <Aviso titulo="No se pudo leer el corpus">{errorDocs}</Aviso>}
        {errorReindex && <Aviso titulo="Falló la reindexación">{errorReindex}</Aviso>}

        {resultadoReindex && (
          <Aviso tono="info" titulo="Reindexación terminada">
            <p>
              {resultadoReindex.sin_cambios
                ? 'No había cambios: el índice ya estaba al día.'
                : `Procesados ${resultadoReindex.procesados.length} archivo(s): ${resultadoReindex.procesados.join(', ')}.`}
            </p>
            <p className="mt-1 text-xs">
              Índice: {resultadoReindex.chunks} chunks ·{' '}
              {(resultadoReindex.duracion_s ?? 0).toFixed(1)} s
            </p>
          </Aviso>
        )}

        <div className="overflow-x-auto rounded-lg border border-app-border bg-app-surface">
          {cargandoDocs ? (
            <div className="flex items-center gap-3 px-4 py-6 text-sm text-app-muted">
              <Spinner />
              <span>cargando documentos…</span>
            </div>
          ) : documentos.length === 0 ? (
            <p className="px-4 py-6 text-sm text-app-muted">
              Todavía no hay documentos indexados. Usá “Reindexar” para construir el índice.
            </p>
          ) : (
            <table className="w-full text-left text-sm">
              <caption className="sr-only">Documentos del corpus indexado</caption>
              <thead>
                <tr className="border-b border-app-border text-xs uppercase tracking-[0.1em] text-app-muted">
                  <th scope="col" className="px-4 py-2.5 font-semibold">
                    Archivo
                  </th>
                  <th scope="col" className="px-4 py-2.5 font-semibold">
                    Documento
                  </th>
                  <th scope="col" className="px-4 py-2.5 text-right font-semibold">
                    Chunks
                  </th>
                  <th scope="col" className="px-4 py-2.5 text-right font-semibold">
                    Palabras
                  </th>
                </tr>
              </thead>
              <tbody>
                {documentos.map((doc) => (
                  <tr key={doc.archivo} className="border-b border-app-border last:border-0">
                    <td className="px-4 py-3 align-top font-mono text-xs text-app-fg">{doc.archivo}</td>
                    <td className="px-4 py-3 align-top">
                      <span className="text-app-fg">{doc.documento}</span>
                      {doc.actualizado && (
                        <span className="mt-0.5 block text-xs text-app-muted">
                          {new Date(doc.actualizado).toLocaleString('es-AR')}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right align-top font-mono text-app-fg">{doc.chunks}</td>
                    <td className="px-4 py-3 text-right align-top font-mono text-app-fg">
                      {doc.palabras.toLocaleString('es-AR')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      <section aria-labelledby="titulo-busqueda" className="space-y-3">
        <div>
          <h2 id="titulo-busqueda" className="text-lg font-semibold text-app-fg">
            Buscar en el corpus
          </h2>
          <p className="text-xs text-app-muted">
            Recuperación directa por similitud, sin pasar por el modelo de lenguaje.
          </p>
        </div>

        <form onSubmit={correrBusqueda} className="flex flex-wrap gap-2">
          <label htmlFor="buscar-corpus" className="sr-only">
            Término a buscar en el corpus
          </label>
          <input
            id="buscar-corpus"
            type="search"
            value={consulta}
            onChange={(e) => setConsulta(e.target.value)}
            placeholder="Ej.: objeto a petit"
            className="min-w-0 flex-1 rounded-lg border border-app-border bg-app-surface px-4 py-2.5 text-app-fg placeholder:text-app-muted focus:border-app-accent"
          />
          <button
            type="submit"
            disabled={!consulta.trim() || buscando}
            className="inline-flex items-center gap-2 rounded-md bg-app-accent px-4 py-2 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {buscando ? <Spinner className="border-white/40 border-t-white" /> : null}
            Buscar
          </button>
        </form>

        {errorBusqueda && <Aviso titulo="Falló la búsqueda">{errorBusqueda}</Aviso>}

        {resultados.length > 0 && (
          <ul className="space-y-3">
            {resultados.map((fragmento) => (
              <li
                key={fragmento.id}
                className="rounded-lg border border-app-border bg-app-surface p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-app-fg">
                      {fragmento.capitulo || fragmento.documento}
                    </p>
                    {fragmento.seccion && <p className="text-xs text-app-muted">{fragmento.seccion}</p>}
                    <p className="mt-1 font-mono text-xs text-app-muted">{fragmento.archivo}</p>
                  </div>
                  <span className="shrink-0 rounded-full border border-app-border px-2 py-0.5 font-mono text-xs text-app-fg">
                    {fragmento.score.toFixed(2)}
                  </span>
                </div>
                <p className="mt-3 font-serif text-sm leading-relaxed text-app-fg">«{fragmento.texto}»</p>
                <p className="mt-2 text-xs text-app-muted">{fragmento.palabras} palabras</p>
              </li>
            ))}
          </ul>
        )}

        {busquedaHecha && resultados.length === 0 && !buscando && !errorBusqueda && (
          <p className="rounded-lg border border-dashed border-app-border bg-app-surface px-4 py-6 text-sm text-app-muted">
            No hay fragmentos que coincidan con esa búsqueda.
          </p>
        )}
      </section>
    </div>
  )
}
