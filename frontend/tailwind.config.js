/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        surface:  "#0f1117",
        panel:    "#161b27",
        border:   "#1e2535",
        accent:   "#f97316",
        alert:    "#ef4444",
        muted:    "#6b7280",
        text:     "#e2e8f0",
      },
      fontFamily: { mono: ["JetBrains Mono", "monospace"] },
    },
  },
  plugins: [],
}
