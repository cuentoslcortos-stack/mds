import { useCallback, useEffect, useState } from 'react'
import { getHealth, setMotor } from './api'
import type { Health } from './types'
import { useVista } from './hooks/useVista'
import BarraEstado from './components/BarraEstado'
import Consulta from './components/Consulta'
import InformeMds from './components/InformeMds'
import Biblioteca from './components/Biblioteca'
import { Aviso } from './components/Piezas'

type Tema = 'claro' | 'oscuro'

function temaInicial(): Tema {
  const guardado = localStorage.getItem('mds-tema')
  if (guardado === 'claro' || guardado === 'oscuro') return guardado
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'oscuro' : 'claro'
}

export default function App() {
  const [vista, ir] = useVista()
  const [salud, setSalud] = useState<Health | null>(null)
  const [errorSalud, setErrorSalud] = useState<string | null>(null)
  const [tema, setTema] = useState<Tema>(temaInicial)
  const [motor, setPolitica] = useState<string | null>(null)
  const [errorMotor, setErrorMotor] = useState<string | null>(null)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', tema === 'oscuro' ? 'dark' : 'light')
    localStorage.setItem('mds-tema', tema)
  }, [tema])

  const refrescarSalud = useCallback(async () => {
    try {
      const datos = await getHealth()
      setSalud(datos)
      setPolitica(datos.nube?.politica ?? 'local')
      setErrorSalud(null)
    } catch (error) {
      setSalud(null)
      setErrorSalud(error instanceof Error ? error.message : 'Error desconocido.')
    }
  }, [])

  /** Cambia el motor del informe MDS en caliente (local / nube gratis). */
  const cambiarMotor = useCallback(
    async (modo: string) => {
      try {
        await setMotor(modo)
        setErrorMotor(null)
      } catch (error) {
        setErrorMotor(error instanceof Error ? error.message : 'No se pudo cambiar el motor.')
      }
      await refrescarSalud()
    },
    [refrescarSalud],
  )

  useEffect(() => {
    void refrescarSalud()
    const temporizador = window.setInterval(() => void refrescarSalud(), 15000)
    return () => window.clearInterval(temporizador)
  }, [refrescarSalud])

  const chunks = salud?.indice?.chunks ?? 0
  const sinOllama = Boolean(salud) && salud?.ollama === false
  const indiceVacio = Boolean(salud) && salud?.indice !== undefined && chunks === 0

  return (
    <div className="min-h-screen bg-app-bg text-app-fg">
      <BarraEstado
        salud={salud}
        errorSalud={errorSalud}
        vista={vista}
        ir={ir}
        tema={tema}
        alternarTema={() => setTema((prev) => (prev === 'claro' ? 'oscuro' : 'claro'))}
        motor={motor}
        cambiarMotor={(modo) => void cambiarMotor(modo)}
      />

      <main className="mx-auto max-w-5xl px-4 py-6 pb-16">
        {errorMotor && (
          <div className="mb-6">
            <Aviso tono="aviso" titulo="No se pudo cambiar el motor">
              <p>{errorMotor}</p>
            </Aviso>
          </div>
        )}
        {errorSalud && (
          <div className="mb-6">
            <Aviso titulo="El motor RAG no responde">
              <p>{errorSalud}</p>
              <p className="mt-1 text-xs">
                Verificá que el backend esté levantado (el proxy del dev server apunta a
                <span className="font-mono"> VITE_API_TARGET</span>) y recargá la página.
              </p>
            </Aviso>
          </div>
        )}

        {sinOllama && (
          <div className="mb-6">
            <Aviso tono="aviso" titulo="Ollama no está disponible">
              <p>
                El índice está construido, pero el modelo no responde: sin Ollama no hay
                embeddings nuevos ni redacción de respuestas.
              </p>
              <p className="mt-1 text-xs">
                Levantá Ollama y recargá. Si vas a incorporar .md nuevos, reindexá después.
              </p>
            </Aviso>
          </div>
        )}

        {indiceVacio && (
          <div className="mb-6">
            <Aviso
              tono="aviso"
              titulo="El índice está vacío"
              acciones={
                <button
                  type="button"
                  onClick={() => ir('biblioteca')}
                  className="rounded-md border border-app-accent px-3 py-1.5 text-xs font-semibold text-app-accent"
                >
                  Ir a Biblioteca
                </button>
              }
            >
              <p>No hay fragmentos indexados todavía: las consultas no van a devolver nada.</p>
              <p className="mt-1 text-xs">
                Andá a Biblioteca y presioná “Reindexar” para construir el índice del corpus.
              </p>
            </Aviso>
          </div>
        )}

        {/* Las tres vistas quedan MONTADAS y se ocultan con CSS: si se
            desmontaran al cambiar de pestana, se perderia la respuesta (y el
            formulario) que ya se genero. */}
        <div className={vista === 'consulta' ? 'block' : 'hidden'}>
          <Consulta />
        </div>
        <div className={vista === 'informe' ? 'block' : 'hidden'}>
          <InformeMds />
        </div>
        <div className={vista === 'biblioteca' ? 'block' : 'hidden'}>
          <Biblioteca alReindexar={() => void refrescarSalud()} />
        </div>
      </main>

      <footer className="border-t border-app-border px-4 py-6 text-center text-xs text-app-muted">
        Sistema MDS · lectura:{''}
        <span className="font-mono">Escritos 1-2, Seminarios 3 y 5</span> · la interfaz cita
        siempre el fragmento del corpus del que proviene cada afirmación.
      </footer>
    </div>
  )
}
