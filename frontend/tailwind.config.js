/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f2f6ff",
          100: "#e3ebff",
          500: "#3a5bfd",
          600: "#2c47e0",
          700: "#2137b8",
        },
      },
    },
  },
  plugins: [],
}
