import { useEffect, useRef, useState } from 'react'

/**
 * Estado que sobrevive al cambio de vista y a la recarga de la pagina.
 *
 * Sin esto, una respuesta que tardo 2,5 minutos en generarse se perdia al
 * cambiar de pestana (el componente se desmontaba) o al recargar con F5.
 */
export function usePersistente<T>(
  clave: string,
  inicial: T,
): [T, (valor: T | ((prev: T) => T)) => void] {
  const [valor, setValor] = useState<T>(() => {
    try {
      const crudo = window.sessionStorage.getItem(clave)
      return crudo === null ? inicial : (JSON.parse(crudo) as T)
    } catch {
      return inicial
    }
  })

  const ref = useRef(valor)
  useEffect(() => {
    ref.current = valor
    try {
      window.sessionStorage.setItem(clave, JSON.stringify(valor))
    } catch {
      // sessionStorage lleno o bloqueado: el estado sigue funcionando en memoria
    }
  }, [clave, valor])

  return [valor, setValor]
}
