import { colors, fontFamily, radius } from "./src/theme/tokens.js";

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      // Palette de marque centralisée (cf. src/theme/tokens.js).
      colors: {
        brand: colors.brand,
        night: colors.night,
        surface: colors.surface,
        accent: colors.accent,
      },
      fontFamily,
      borderRadius: {
        card: radius.card,
      },
      boxShadow: {
        // Ombres légères (ton visuel : confiance, espace blanc).
        soft: "0 1px 3px rgba(15,23,42,0.06), 0 1px 2px rgba(15,23,42,0.04)",
      },
    },
  },
  plugins: [],
};
