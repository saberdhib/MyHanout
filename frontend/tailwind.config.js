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
        pill: radius.pill,
        xl2: "1.25rem",
      },
      boxShadow: {
        // Ombres légères (ton visuel : confiance, espace blanc).
        soft: "0 1px 3px rgba(15,23,42,0.06), 0 1px 2px rgba(15,23,42,0.04)",
        card: "0 10px 30px -12px rgba(15,23,42,0.18)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.4s cubic-bezier(0.16,1,0.3,1) both",
      },
    },
  },
  plugins: [],
};
