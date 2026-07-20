import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: { ink: "#111510", gravel: "#c7ff2e", moss: "#243227", fog: "#eef1eb" },
      boxShadow: { card: "0 18px 50px rgba(22, 32, 24, 0.10)" },
    },
  },
  plugins: [],
} satisfies Config;

