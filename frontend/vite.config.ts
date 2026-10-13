import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // 不做 rewrite：后端路由本身就带 /api 前缀。
        // 这样 dev 与「后端托管 dist」的生产环境行为完全一致，
        // 避免 dev 能跑、Docker 里白屏这类问题。
      },
    },
  },
})
