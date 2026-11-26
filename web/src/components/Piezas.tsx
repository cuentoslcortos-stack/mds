import { useCallback, useEffect, useState, type ReactNode } from 'react'

export function Spinner({ className = '' }: { className?: string }) {
  return (
    <span
      role="status"
      aria-label="Procesando"
      className={`inline-block h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-app-border border-t-app-accent ${className}`}
    />
  )
}

export type TonoAviso = 'error' | 'aviso' | 'info'

const ESTILO_AVISO: Record<TonoAviso, string> = {
  error: 'border-app-danger/40 bg-app-danger/10 text-app-danger',
  aviso: 'border-app-accent/40 bg-app-accent-soft text-app-fg',
  info: 'border-app-border bg-app-raised text-app-fg',
}

export function Aviso({
  tono = 'error',
  titulo,
  children,
  acciones,
}: {
  tono?: TonoAviso
  titulo: string
  children?: ReactNode
  acciones?: ReactNode
}) {
  return (
    <div
      role={tono === 'error' ? 'alert' : 'status'}
      className={`flex flex-col gap-2 rounded-lg border px-4 py-3 sm:flex-row sm:items-start sm:justify-between ${ESTILO_AVISO[tono]}`}
    >
      <div className="min-w-0">
        <p className="text-sm font-semibold">{titulo}</p>
        {children && <div className="mt-1 text-sm leading-relaxed">{children}</div>}
      </div>
      {acciones && <div className="flex shrink-0 gap-2">{acciones}</div>}
    </div>
  )
}

export function EstadoVacio({
  titulo,
  children,
}: {
  titulo: string
  children?: ReactNode
}) {
  return (
    <div className="rounded-lg border border-dashed border-app-border bg-app-surface px-6 py-10 text-center">
      <p className="font-serif text-lg text-app-fg">{titulo}</p>
      {children && <div className="mx-auto mt-2 max-w-prose text-sm leading-relaxed text-app-muted">{children}</div>}
    </div>
  )
}

/** Botón "copiar" con realimentación accesible. */
export function BotonCopiar({ texto, etiqueta = 'Copiar respuesta' }: { texto: string; etiqueta?: string }) {
  const [estado, setEstado] = useState<'inactivo' | 'copiado' | 'error'>('inactivo')

  useEffect(() => {
    if (estado === 'inactivo') return
    const t = window.setTimeout(() => setEstado('inactivo'), 2200)
    return () => window.clearTimeout(t)
  }, [estado])

  const copiar = useCallback(async () => {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(texto)
      } else {
        const area = document.createElement('textarea')
        area.value = texto
        area.setAttribute('readonly', '')
        area.style.position = 'fixed'
        area.style.opacity = '0'
        document.body.appendChild(area)
        area.select()
        document.execCommand('copy')
        document.body.removeChild(area)
      }
      setEstado('copiado')
    } catch {
      setEstado('error')
    }
  }, [texto])

  return (
    <button
      type="button"
      onClick={copiar}
      disabled={!texto.trim()}
      className="inline-flex items-center gap-2 rounded-md border border-app-border bg-app-surface px-3 py-1.5 text-xs font-medium text-app-muted transition-colors hover:border-app-accent hover:text-app-accent disabled:cursor-not-allowed disabled:opacity-50"
    >
      <span aria-hidden="true">⧉</span>
      {estado === 'copiado' ? 'Copiado' : estado === 'error' ? 'No se pudo copiar' : etiqueta}
    </button>
  )
}
