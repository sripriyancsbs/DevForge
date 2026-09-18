/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        platform: {
          bg: '#09090b',       // zinc-950
          card: '#121215',     // slightly elevated
          cardHover: '#18181b', // zinc-900
          border: '#27272a',   // zinc-800
          subtle: '#3f3f46',   // zinc-700
          muted: '#71717a',    // zinc-500
          text: '#f4f4f5',     // zinc-100
          secondary: '#a1a1aa' // zinc-400
        },
        state: {
          healthy: '#10b981',   // emerald-500
          warning: '#f59e0b',   // amber-500
          failed: '#f43f5e',    // rose-500
          running: '#0284c7',   // sky-600
          pending: '#71717a',   // zinc-500
        }
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
}
