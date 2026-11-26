import type { Fuente } from '../types'

function puntaje(score: number): string {
  return `${score.toFixed(2)}`
}

function colorPuntaje(score: number): string {
  if (score >= 0.7) return 'text-app-ok'
  if (score >= 0.5) return 'text-app-fg'
  return 'text-app-muted'
}

export function TarjetaFuente({ fuente, indice }: { fuente: Fuente; indice: number }) {
  return (
    <article className="flex flex-col gap-2 rounded-lg border border-app-border bg-app-surface p-4">
      <header className="flex flex-wrap items-start justify-between gap-2">
        <h4 className="text-sm font-semibold text-app-fg">
          <span className="mr-2 font-mono text-xs text-app-muted">[{indice + 1}]</span>
          {fuente.documento || fuente.archivo}
        </h4>
        <span
          className={`shrink-0 rounded-full border border-app-border px-2 py-0.5 font-mono text-xs ${colorPuntaje(
            fuente.score,
          )}`}
          title="Score de relevancia"
        >
          {puntaje(fuente.score)}
        </span>
      </header>

      <div className="text-xs leading-relaxed text-app-muted">
        {fuente.capitulo && <p className="text-app-fg">{fuente.capitulo}</p>}
        {fuente.seccion && <p>{fuente.seccion}</p>}
        <p className="mt-1 font-mono">{fuente.archivo}</p>
      </div>

      {fuente.extracto && (
        <blockquote className="border-l-2 border-app-accent pl-3 font-serif text-sm leading-relaxed text-app-fg italic">
          «{fuente.extracto}»
        </blockquote>
      )}

      {typeof fuente.palabras === 'number' && (
        <p className="text-xs text-app-muted">{fuente.palabras} palabras citadas</p>
      )}
    </article>
  )
}

export function Fuentes({ fuentes }: { fuentes: Fuente[] }) {
  if (!fuentes.length) return null

  return (
    <section aria-labelledby="titulo-fuentes" className="mt-8">
      <h3 id="titulo-fuentes" className="mb-3 text-sm font-semibold uppercase tracking-[0.15em] text-app-muted">
        Fuentes citadas ({fuentes.length})
      </h3>
      <div className="grid gap-3 md:grid-cols-2">
        {fuentes.map((fuente, i) => (
          <TarjetaFuente key={`${fuente.archivo}-${i}`} fuente={fuente} indice={i} />
        ))}
      </div>
    </section>
  )
}
