import { useMemo, type ReactNode } from 'react'

/**
 * Parser de markdown mínimo (propio, sin dependencias).
 * Soporta: encabezados #..####, párrafos, negritas **, cursivas *,
 * código inline `, listas con guion o numeradas, blockquotes >, separadores ---
 * y TABLAS de markdown (GFM: fila de encabezado + separador |---|---|).
 * Nunca interpreta HTML crudo.
 */

type Bloque =
  | { tipo: 'titulo'; nivel: number; texto: string }
  | { tipo: 'parrafo'; texto: string }
  | { tipo: 'lista'; ordenada: boolean; items: string[] }
  | { tipo: 'cita'; lineas: string[] }
  | { tipo: 'tabla'; encabezados: string[]; filas: string[][] }
  | { tipo: 'separador' }

const RE_LISTA = /^([-*+]|\d+[.)])\s+(.*)$/
const RE_TITULO = /^(#{1,6})\s+(.*)$/
const RE_SEPARADOR = /^(-{3,}|\*{3,}|_{3,})$/
const RE_FASE = /^fase\s*\d+/i
const RE_FILA_TABLA = /^\|(.+)\|\s*$/
const RE_SEP_TABLA = /^\|(?:\s*:?-+:?\s*\|)+\s*$/

/** Convierte una fila "| a | b |" en sus celdas, sin los bordes. */
function celdas(linea: string): string[] {
  return linea
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((c) => c.trim())
}

/** "Fase 1: La Escucha Activa" → true (admite el wrapper **...** o un encabezado). */
export function esTituloDeFase(texto: string): string | null {
  const limpio = texto.trim()
  const enNegrita = /^\*\*(.+)\*\*$/.exec(limpio)
  const interior = (enNegrita ? enNegrita[1] : limpio).trim()
  if (!RE_FASE.test(interior)) return null
  return interior
}

export function parseMarkdown(md: string): Bloque[] {
  const lineas = md.split(/\r?\n/)
  const bloques: Bloque[] = []
  let parrafo: string[] = []
  let i = 0

  const cerrarParrafo = () => {
    if (parrafo.length) {
      bloques.push({ tipo: 'parrafo', texto: parrafo.join('\n') })
      parrafo = []
    }
  }

  while (i < lineas.length) {
    const cruda = lineas[i]
    const linea = cruda.trim()

    if (!linea) {
      cerrarParrafo()
      i += 1
      continue
    }

    const titulo = RE_TITULO.exec(linea)
    if (titulo) {
      cerrarParrafo()
      bloques.push({ tipo: 'titulo', nivel: titulo[1].length, texto: titulo[2].trim() })
      i += 1
      continue
    }

    if (RE_SEPARADOR.test(linea)) {
      cerrarParrafo()
      bloques.push({ tipo: 'separador' })
      i += 1
      continue
    }

    if (linea.startsWith('>')) {
      cerrarParrafo()
      const cita: string[] = []
      while (i < lineas.length && lineas[i].trim().startsWith('>')) {
        cita.push(lineas[i].trim().replace(/^>\s?/, ''))
        i += 1
      }
      bloques.push({ tipo: 'cita', lineas: cita })
      continue
    }

    // Tabla de markdown: encabezado + separador |---|---|
    if (RE_FILA_TABLA.test(linea)) {
      const separadora = (lineas[i + 1] ?? '').trim()
      if (RE_SEP_TABLA.test(separadora)) {
        cerrarParrafo()
        const encabezados = celdas(linea)
        i += 2
        const filas: string[][] = []
        while (i < lineas.length && lineas[i].trim().startsWith('|')) {
          filas.push(celdas(lineas[i]))
          i += 1
        }
        bloques.push({ tipo: 'tabla', encabezados, filas })
        continue
      }
    }

    if (RE_LISTA.test(linea)) {
      cerrarParrafo()
      const ordenada = /^\d/.test(RE_LISTA.exec(linea)![1])
      const items: string[] = []
      while (i < lineas.length) {
        const item = RE_LISTA.exec(lineas[i].trim())
        if (!item) break
        items.push(item[2])
        i += 1
      }
      bloques.push({ tipo: 'lista', ordenada, items })
      continue
    }

    parrafo.push(cruda)
    i += 1
  }

  cerrarParrafo()
  return bloques
}

const RE_INLINE = /(`[^`\n]+`)|(\*\*[^*\n]+?\*\*)|(\*[^*\n]+?\*)/g

/** Convierte **negrita**, *cursiva* y `código` en nodos React. */
export function renderInline(texto: string): ReactNode[] {
  const nodos: ReactNode[] = []
  let ultimo = 0
  let clave = 0
  const patron = new RegExp(RE_INLINE.source, 'g')
  let coincidencia = patron.exec(texto)

  while (coincidencia !== null) {
    if (coincidencia.index > ultimo) nodos.push(texto.slice(ultimo, coincidencia.index))
    const bruto = coincidencia[0]
    if (bruto.startsWith('`')) {
      nodos.push(
        <code
          key={clave++}
          className="rounded bg-app-raised px-1.5 py-0.5 font-mono text-[0.85em] text-app-fg"
        >
          {bruto.slice(1, -1)}
        </code>,
      )
    } else if (bruto.startsWith('**')) {
      nodos.push(
        <strong key={clave++} className="font-semibold text-app-fg">
          {bruto.slice(2, -2)}
        </strong>,
      )
    } else {
      nodos.push(
        <em key={clave++} className="italic">
          {bruto.slice(1, -1)}
        </em>,
      )
    }
    ultimo = coincidencia.index + bruto.length
    coincidencia = patron.exec(texto)
  }

  if (ultimo < texto.length) nodos.push(texto.slice(ultimo))
  return nodos
}

function EncabezadoFase({ texto }: { texto: string }) {
  const partes = /^(fase\s*\d+)\s*[:.—–-]?\s*(.*)$/i.exec(texto)
  const etiqueta = partes ? partes[1] : 'Fase'
  const resto = partes ? partes[2].trim() : texto

  return (
    <div className="my-6 border-l-4 border-app-accent bg-app-accent-soft px-4 py-3">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:gap-3">
        <span className="text-xs font-semibold uppercase tracking-[0.2em] text-app-accent">
          {etiqueta}
        </span>
        {resto && (
          <h2 className="font-serif text-lg leading-snug font-semibold text-app-fg">{resto}</h2>
        )}
      </div>
    </div>
  )
}

const CLASES_TITULO: Record<number, string> = {
  1: 'mt-8 mb-3 text-2xl font-semibold tracking-tight',
  2: 'mt-7 mb-3 text-xl font-semibold tracking-tight',
  3: 'mt-6 mb-2 text-lg font-semibold',
  4: 'mt-5 mb-2 text-sm font-semibold uppercase tracking-[0.15em] text-app-muted',
  5: 'mt-5 mb-2 text-sm font-semibold text-app-muted',
  6: 'mt-4 mb-2 text-sm font-semibold text-app-muted',
}

export function Markdown({ texto, cursor = false }: { texto: string; cursor?: boolean }) {
  const bloques = useMemo(() => parseMarkdown(texto), [texto])

  return (
    <div className="max-w-none text-[0.98rem] leading-7 text-app-fg">
      {bloques.map((bloque, i) => {
        const esUltimo = i === bloques.length - 1

        switch (bloque.tipo) {
          case 'titulo': {
            const fase = esTituloDeFase(bloque.texto)
            if (fase) return <EncabezadoFase key={i} texto={fase} />
            const Nivel = `h${Math.min(bloque.nivel, 4)}` as 'h1' | 'h2' | 'h3' | 'h4'
            return (
              <Nivel key={i} className={CLASES_TITULO[bloque.nivel] ?? CLASES_TITULO[4]}>
                {renderInline(bloque.texto)}
                {esUltimo && cursor}
              </Nivel>
            )
          }
          case 'parrafo': {
            const fase = esTituloDeFase(bloque.texto)
            if (fase) return <EncabezadoFase key={i} texto={fase} />
            const soloNegrita = /^\*\*(.+)\*\*$/.test(bloque.texto.trim())
            if (soloNegrita) {
              return (
                <p key={i} className="mt-6 mb-2 text-base font-semibold text-app-fg">
                  {renderInline(bloque.texto.trim())}
                  {esUltimo && cursor}
                </p>
              )
            }
            return (
              <p key={i} className="mt-4 mb-4 whitespace-pre-line">
                {renderInline(bloque.texto)}
                {esUltimo && cursor}
              </p>
            )
          }
          case 'lista': {
            const Tag = bloque.ordenada ? 'ol' : 'ul'
            return (
              <Tag
                key={i}
                className={`mt-3 mb-4 space-y-1 pl-6 text-app-fg ${
                  bloque.ordenada ? 'list-decimal' : 'list-disc'
                } marker:text-app-muted`}
              >
                {bloque.items.map((item, j) => (
                  <li key={j}>{renderInline(item)}</li>
                ))}
                {esUltimo && cursor}
              </Tag>
            )
          }
          case 'cita':
            return (
              <blockquote
                key={i}
                className="my-4 border-l-4 border-app-border pl-4 font-serif text-app-muted italic"
              >
                {bloque.lineas.map((linea, j) => (
                  <p key={j} className="my-1">
                    {renderInline(linea)}
                  </p>
                ))}
                {esUltimo && cursor}
              </blockquote>
            )
          case 'separador':
            return <hr key={i} className="my-7 border-t border-app-border" />
          case 'tabla':
            return (
              <div key={i} className="my-6 overflow-x-auto rounded-lg border border-app-border">
                <table className="w-full min-w-[620px] border-collapse text-left text-[0.92rem]">
                  <thead>
                    <tr className="border-b-2 border-app-border bg-app-raised">
                      {bloque.encabezados.map((celda, j) => (
                        <th
                          key={j}
                          className="px-3 py-2 font-semibold uppercase tracking-wide text-app-fg"
                        >
                          {renderInline(celda)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {bloque.filas.map((fila, j) => (
                      <tr key={j} className="border-b border-app-border/60 align-top last:border-0">
                        {fila.map((celda, k) => (
                          <td key={k} className="px-3 py-2 text-app-fg">
                            {renderInline(celda)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          default:
            return null
        }
      })}
    </div>
  )
}
