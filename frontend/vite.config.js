import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Fail loudly instead of drifting to a port the API's CORS allowlist rejects.
    port: 5173,
    strictPort: true,
  },
})
