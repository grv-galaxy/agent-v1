/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      boxShadow: {
        glow: '0 24px 80px rgba(20, 184, 166, 0.22)',
      },
    },
  },
  plugins: [],
};
