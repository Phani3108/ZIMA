/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: "#0078d4",   // Microsoft blue — matches Teams
      },
    },
  },
  plugins: [],
};
