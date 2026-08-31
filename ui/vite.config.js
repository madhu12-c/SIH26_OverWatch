import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteSingleFile } from 'vite-plugin-singlefile'

// Everything is inlined into ONE index.html - script, styles, and the data.
//
// This is not a preference. Vite's default output is an ES module, and a
// browser refuses to load ES modules over file:// under CORS. The built page
// opens as a blank white screen when double-clicked, which is exactly how the
// demo is shown - on a laptop and on a phone, with no server and no internet.
//
// A single self-contained file has no such restriction: double-click it, or
// send it over WhatsApp and open it on a phone in airplane mode.
export default defineConfig({
  plugins: [react(), viteSingleFile()],
  base: './',
  build: {
    outDir: 'dist',
    assetsInlineLimit: 100000000,
    cssCodeSplit: false,
    chunkSizeWarningLimit: 5000,
  },
})
