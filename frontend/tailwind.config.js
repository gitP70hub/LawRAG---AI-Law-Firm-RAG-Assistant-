/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Core brand
        indigo: {
          50:  '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          800: '#3730a3',
          900: '#312e81',
        },
        // Sidebar palette
        sidebar: {
          DEFAULT: '#0d1117',
          hover:   '#161b22',
          active:  '#1c2840',
          border:  '#21262d',
          muted:   '#8b949e',
          text:    '#c9d1d9',
        },
        // Surface shades
        surface: {
          DEFAULT: '#f5f6f8',
          card:    '#ffffff',
          hover:   '#f8f9fb',
        },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        '2xs': ['10px', '14px'],
        xs:    ['12px', '16px'],
        sm:    ['13px', '18px'],
        base:  ['15px', '22px'],
      },
      borderRadius: {
        xl:  '12px',
        '2xl': '16px',
        '3xl': '24px',
      },
      boxShadow: {
        card:    '0 1px 3px 0 rgb(0 0 0 / 0.05), 0 1px 2px -1px rgb(0 0 0 / 0.05)',
        'card-md': '0 4px 12px -2px rgb(0 0 0 / 0.08), 0 2px 6px -2px rgb(0 0 0 / 0.05)',
        'card-lg': '0 8px 24px -4px rgb(0 0 0 / 0.10), 0 4px 8px -4px rgb(0 0 0 / 0.06)',
        glow:    '0 0 0 3px rgb(99 102 241 / 0.15)',
      },
      spacing: {
        sidebar: '248px',
        header:  '60px',
      },
      animation: {
        'fade-in':   'fadeIn 0.25s ease-out both',
        'slide-up':  'slideUp 0.3s cubic-bezier(.16,1,.3,1) both',
        'pulse-dot': 'pulseDot 1.4s ease-in-out infinite',
        'shimmer':   'shimmer 1.6s linear infinite',
      },
      keyframes: {
        fadeIn:    { '0%': { opacity: '0' },                                           '100%': { opacity: '1' } },
        slideUp:   { '0%': { opacity: '0', transform: 'translateY(10px)' },            '100%': { opacity: '1', transform: 'translateY(0)' } },
        pulseDot:  { '0%,100%': { opacity: '0.9' },                                    '50%':  { opacity: '0.2' } },
        shimmer:   { '0%':   { backgroundPosition: '-400px 0' },                       '100%': { backgroundPosition: '400px 0' } },
      },
    },
  },
  plugins: [],
};
