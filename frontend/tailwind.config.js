/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        democrat: '#2563eb',    // Blue
        republican: '#dc2626',  // Red
        independent: '#7c3aed', // Purple
      },
    },
  },
  plugins: [],
}
