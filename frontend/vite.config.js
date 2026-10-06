import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/auth': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          if (id.includes('node_modules')) {
            if (id.includes('react-router')) return 'router'
            if (id.includes('react') || id.includes('scheduler')) return 'react-vendor'
            if (id.includes('@tanstack')) return 'query'
            if (id.includes('zustand')) return 'zustand'
            if (id.includes('formik') || id.includes('yup')) return 'form'
            if (id.includes('axios')) return 'axios'
            if (id.includes('@radix-ui')) return 'radix'
            if (id.includes('framer-motion')) return 'motion'
            if (id.includes('lucide-react') || id.includes('clsx') || id.includes('tailwind-merge') || id.includes('class-variance-authority')) return 'ui-helpers'
            // let remaining vendor code stay in main chunk to avoid circular
          }
        },
      },
    },
  },
})
