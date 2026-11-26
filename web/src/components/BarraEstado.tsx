import type { Health } from '../types'
import { etiquetaDeVista, VISTAS, type Vista } from '../hooks/useVista'

function Punto({ ok }: { ok: boolean }) {
  return (
    <span
      aria-hidden="true"
      className={`inline-block h-2 w-2 rounded-full ${ok ? 'bg-app-ok' : 'bg-app-danger'}`}
    />
  )
}

function Dato({ etiqueta, valor }: { etiqueta: string; valor: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="text-app-muted">{etiqueta}</span>
      <span className="font-mono text-app-fg">{valor}</span>
    </span>
  )
}

export default function BarraEstado({
  salud,
  errorSalud,
  vista,
  ir,
  tema,
  alternarTema,
  motor,
  cambiarMotor,
}: {
  salud: Health | null
  errorSalud: string | null
  vista: Vista
  ir: (v: Vista) => void
  tema: 'claro' | 'oscuro'
  alternarTema: () => void
  motor: string | null
  cambiarMotor: (modo: string) => void
}) {
  const indice = salud?.indice
  const chunks = indice?.chunks ?? 0
  const documentos = indice?.documentos ?? 0
  const politica = salud?.nube?.politica ?? motor ?? 'local'
  const enNube = politica !== 'local'
  // Con la politica en nube el informe lo escribe el modelo de la nube; en
  // local, el modelo grande de Ollama. La barra tiene que decir el real.
  const modeloInforme = enNube
    ? (salud?.nube?.modelo ?? '—')
    : (salud?.llm_model_b ?? '—')

  return (
    <header className="sticky top-0 z-20 border-b border-app-border bg-app-surface">
      <div className="mx-auto max-w-5xl px-4 pt-3 pb-2">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="font-serif text-lg leading-tight font-semibold text-app-fg">
              MDS · Corpus lacaniano
            </h1>
            <p className="text-xs text-app-muted">Escritos 1-2 · Seminarios 3 y 5</p>
          </div>

          <div className="flex items-center gap-2">
            {salud ? (
              <span
                className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium ${
                  salud.ollama
                    ? 'border-app-ok/40 bg-app-ok/10 text-app-ok'
                    : 'border-app-danger/40 bg-app-danger/10 text-app-danger'
                }`}
              >
                <Punto ok={salud.ollama} />
                {salud.ollama ? 'Ollama online' : 'Ollama offline'}
              </span>
            ) : (
              <span className="inline-flex items-center gap-2 rounded-full border border-app-danger/40 bg-app-danger/10 px-3 py-1 text-xs font-medium text-app-danger">
                <Punto ok={false} />
                {errorSalud ? 'Sin conexión' : 'Consultando…'}
              </span>
            )}

            <button
              type="button"
              onClick={alternarTema}
              aria-label={tema === 'claro' ? 'Activar modo oscuro' : 'Activar modo claro'}
              className="flex h-8 w-8 items-center justify-center rounded-md border border-app-border text-sm text-app-muted transition-colors hover:border-app-accent hover:text-app-accent"
            >
              <span aria-hidden="true">{tema === 'claro' ? '☾' : '☀'}</span>
            </button>
          </div>
        </div>

        <nav aria-label="Vistas del sistema" className="mt-3 flex gap-1 overflow-x-auto">
          {VISTAS.map((v) => {
            const activa = v === vista
            return (
              <button
                key={v}
                type="button"
                onClick={() => ir(v)}
                aria-current={activa ? 'page' : undefined}
                className={`shrink-0 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  activa
                    ? 'bg-app-accent-soft text-app-accent'
                    : 'text-app-muted hover:bg-app-raised hover:text-app-fg'
                }`}
              >
                {etiquetaDeVista(v)}
              </button>
            )
          })}
        </nav>

        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 pb-1 text-xs">
          {salud ? (
            <>
              <Dato etiqueta="embeddings" valor={salud.embed_model || '—'} />
              <Dato etiqueta="consulta" valor={salud.llm_model || '—'} />
              <Dato etiqueta="informe MDS" valor={modeloInforme} />
              <Dato etiqueta="chunks" valor={String(chunks)} />
              <Dato etiqueta="documentos" valor={String(documentos)} />
              {indice?.actualizado && (
                <span className="text-app-muted">
                  índice actualizado{' '}
                  <span className="font-mono text-app-fg">
                    {new Date(indice.actualizado).toLocaleString('es-AR')}
                  </span>
                </span>
              )}
              <label className="inline-flex items-center gap-1.5">
                <span className="text-app-muted">motor del informe</span>
                <select
                  value={politica}
                  onChange={(e) => cambiarMotor(e.target.value)}
                  title={
                    enNube
                      ? 'El caso sale a la nube (modelo gratis). Para 100% local elegí "local".'
                      : 'Todo corre en tu maquina: nada sale de la red.'
                  }
                  className="rounded-md border border-app-border bg-app-raised px-2 py-0.5 font-mono text-xs text-app-fg"
                >
                  <option value="local">local (offline)</option>
                  <option value="auto">nube gratis + local</option>
                  <option value="nube">nube gratis</option>
                </select>
              </label>
            </>
          ) : (
            <span className="text-app-muted">Esperando respuesta del motor RAG…</span>
          )}
        </div>
      </div>
    </header>
  )
}
