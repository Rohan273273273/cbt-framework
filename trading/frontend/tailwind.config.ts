import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0d1117',
        panel: '#1e2329',
        border: '#2a2f3a',
        accent: '#26a69a',
        red: '#ef5350',
        green: '#26a69a',
        text: '#d1d4dc',
        muted: '#787b86',
      }
    }
  },
  plugins: []
} satisfies Config
