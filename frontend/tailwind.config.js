/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        border: '#1e2a3a',
        input: '#1e2a3a',
        ring: '#c2e94e',
        background: '#0a0e14',
        foreground: '#f0f2f5',
        te: {
          surface: '#0a0e14',
          'surface-dim': '#060a10',
          'surface-bright': '#141c28',
          'surface-container-lowest': '#0d1219',
          'surface-container-low': '#111923',
          'surface-container': '#16202e',
          'surface-container-high': '#1c2838',
          'surface-container-highest': '#233042',
          'on-surface': '#f0f2f5',
          'on-surface-variant': '#8a95a5',
          'inverse-surface': '#e8ecf0',
          'inverse-on-surface': '#0a0e14',
          outline: '#3d4f63',
          'outline-variant': '#1e2a3a',
        },
        primary: {
          DEFAULT: '#c2e94e',
          foreground: '#0a0e14',
          container: '#3a5a10',
          'container-foreground': '#d4f570',
          fixed: '#d4f570',
          'fixed-dim': '#a8d435',
        },
        secondary: {
          DEFAULT: '#64748b',
          foreground: '#f0f2f5',
          container: '#1e2a3a',
          'container-foreground': '#94a3b8',
        },
        tertiary: {
          DEFAULT: '#3b82f6',
          foreground: '#ffffff',
          container: '#1e3a5f',
          'container-foreground': '#93c5fd',
        },
        destructive: {
          DEFAULT: '#ef4444',
          foreground: '#ffffff',
          container: '#450a0a',
          'container-foreground': '#fca5a5',
        },
        muted: {
          DEFAULT: '#16202e',
          foreground: '#8a95a5',
        },
        accent: {
          DEFAULT: '#1c2838',
          foreground: '#f0f2f5',
        },
        card: {
          DEFAULT: '#111923',
          foreground: '#f0f2f5',
        },
      },
      borderRadius: {
        lg: '0.75rem',
        md: '0.5rem',
        sm: '0.25rem',
        xl: '1rem',
        '2xl': '1.5rem',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        'display-lg': ['48px', { lineHeight: '1.1', letterSpacing: '-0.02em', fontWeight: '700' }],
        'stats-xl': ['40px', { lineHeight: '1.0', letterSpacing: '-0.03em', fontWeight: '700' }],
        'headline-lg': ['32px', { lineHeight: '1.2', letterSpacing: '-0.01em', fontWeight: '600' }],
        'headline-md': ['24px', { lineHeight: '1.3', fontWeight: '600' }],
        'title-lg': ['20px', { lineHeight: '1.4', fontWeight: '600' }],
        'body-lg': ['16px', { lineHeight: '1.6', fontWeight: '400' }],
        'body-md': ['14px', { lineHeight: '1.5', fontWeight: '400' }],
        'label-md': ['12px', { lineHeight: '1.2', letterSpacing: '0.05em', fontWeight: '500' }],
      },
      spacing: {
        gutter: '24px',
        base: '8px',
        xs: '4px',
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
}