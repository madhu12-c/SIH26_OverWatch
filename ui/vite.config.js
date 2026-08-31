import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base: './' is REQUIRED. Without it the built dist/index.html asks for
// /assets/... from the filesystem root and renders a blank white page when
// opened by double-clicking - which is exactly how the demo is shown.
export default defineConfig({
  plugins: [react()],
  base: './',
  build: { outDir: 'dist', assetsInlineLimit: 4096 },
})
