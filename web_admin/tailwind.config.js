/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        darkBg: "#0f172a",
        darkCard: "rgba(255, 255, 255, 0.05)",
        darkBorder: "rgba(255, 255, 255, 0.1)",
        brand: "#3b82f6",
        brandHover: "#2563eb",
      }
    },
  },
  plugins: [],
}
