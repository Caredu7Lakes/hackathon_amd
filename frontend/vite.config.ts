import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Proxy de desenvolvimento: tudo que comeca com /api e encaminhado
// para o backend FastAPI no container (porta 8000). Como o navegador
// so ve a origem do proprio Vite (5173), nao ha CORS — e a chave da
// Anthropic nunca toca o frontend: o React fala so com /api local.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
