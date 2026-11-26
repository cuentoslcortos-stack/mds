import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Destino del backend RAG. Se puede overridear con VITE_API_TARGET.
const apiTarget = process.env.VITE_API_TARGET ?? 'http://127.0.0.1:8765'

// El front siempre habla a rutas relativas (/api/...) y el server de Vite las reenvía.
const proxy = {
  '/api': {
    target: apiTarget,
    changeOrigin: true,
    secure: false,
  },
}

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy,
  },
  preview: {
    port: 4173,
    proxy,
  },
})
