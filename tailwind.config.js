/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        orange: {
          400: '#FF8A65',
          500: '#F95E3F',
          600: '#E64A2E',
        },
      },
      fontFamily: {
        sans: ['Nunito', 'Segoe UI', 'system-ui', 'sans-serif'],
        display: ['Fredoka One', 'Nunito', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
