/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Nunito', 'system-ui', '-apple-system', 'sans-serif'],
      },
      colors: {
        primary: {
          50: '#eef6ff',
          100: '#d9ebff',
          200: '#bcdaff',
          300: '#8ec2ff',
          400: '#59a0ff',
          500: '#3b7bfc',
          600: '#1f56f1',
          700: '#1a43de',
          800: '#1c38b4',
          900: '#1c338e',
        },
        surface: {
          50: '#e8eaf0',
          100: '#c5c9d6',
          200: '#9ea4b8',
          300: '#777f9b',
          400: '#596285',
          500: '#3b4670',
          600: '#333d65',
          700: '#2a3257',
          800: '#212849',
          900: '#1a1f3a',
          950: '#131729',
        },
      },
      borderRadius: {
        '4xl': '2rem',
      },
      boxShadow: {
        'glow-sm': '0 0 10px -3px rgba(99, 179, 237, 0.3)',
        'glow': '0 0 20px -5px rgba(99, 179, 237, 0.3)',
        'glow-lg': '0 0 30px -5px rgba(99, 179, 237, 0.4)',
        'glow-purple': '0 0 20px -5px rgba(168, 85, 247, 0.4)',
        'inner-glow': 'inset 0 1px 0 0 rgba(255, 255, 255, 0.05)',
      },
    },
  },
  safelist: [
    { pattern: /bg-(sky|green|purple|amber|rose|teal|indigo|orange)-(100|500|900)/ },
    { pattern: /text-(sky|green|purple|amber|rose|teal|indigo|orange)-(300|500|700)/ },
    { pattern: /border-(sky|green|purple|amber|rose|teal|indigo|orange)-(300|500)/ },
  ],
  plugins: [],
}
