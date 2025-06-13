import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Proxy API requests to the FastAPI backend
      '/start_game': 'http://127.0.0.1:8000',
      '/game_state': 'http://127.0.0.1:8000',
      '/play_action': 'http://127.0.0.1:8000',
      '/choose_color': 'http://127.0.0.1:8000',
      '/game_info': 'http://127.0.0.1:8000',
    }
  }
}) 