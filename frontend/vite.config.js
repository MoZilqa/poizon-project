import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// В разработке запросы /api уходят на бэкенд
export default defineConfig({
  plugins: [vue()],
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
