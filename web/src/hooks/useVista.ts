import { useEffect, useState } from 'react'

export type Vista = 'consulta' | 'informe' | 'biblioteca'

export const VISTAS: Vista[] = ['consulta', 'informe', 'biblioteca']

const ETIQUETAS: Record<Vista, string> = {
  consulta: 'Consulta',
  informe: 'Informe MDS',
  biblioteca: 'Biblioteca',
}

export function etiquetaDeVista(vista: Vista): string {
  return ETIQUETAS[vista]
}

function leerHash(): Vista {
  const bruto = window.location.hash.replace(/^#\/?/, '').split('?')[0]
  return (VISTAS as string[]).includes(bruto) ? (bruto as Vista) : 'consulta'
}

/** La vista vive en el hash: recargar no pierde el lugar. */
export function useVista(): [Vista, (v: Vista) => void] {
  const [vista, setVista] = useState<Vista>(leerHash)

  useEffect(() => {
    const alCambiar = () => setVista(leerHash())
    window.addEventListener('hashchange', alCambiar)
    return () => window.removeEventListener('hashchange', alCambiar)
  }, [])

  const ir = (destino: Vista) => {
    if (leerHash() === destino) return
    window.location.hash = `/${destino}`
  }

  return [vista, ir]
}
