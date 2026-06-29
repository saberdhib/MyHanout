/** @type {import('tailwindcss').Config} */
// Palette alignée pixel-près sur l'app (frontend/src/theme/tokens.js).
export default {
  content: ["./src/**/*.{astro,html,js,ts,jsx,tsx,md,mdx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#12B76A",
          dark: "#0E9A59",
          light: "#D1FADF",
          50: "#ECFDF3",
        },
        night: {
          DEFAULT: "#0F172A",
          800: "#1E293B",
          700: "#334155",
        },
        surface: "#F1F5F9",
        accent: { DEFAULT: "#F59E0B", soft: "#FEF3C7" },
      },
      fontFamily: {
        sans: ["Manrope Variable", "Manrope", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      },
      borderRadius: {
        card: "0.875rem",
        xl2: "1.25rem",
      },
      boxShadow: {
        soft: "0 1px 3px rgba(15,23,42,0.06), 0 1px 2px rgba(15,23,42,0.04)",
        card: "0 10px 30px -12px rgba(15,23,42,0.18)",
        glow: "0 30px 80px -20px rgba(18,183,106,0.45)",
      },
      maxWidth: {
        content: "1120px",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(16px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        float: {
          "0%,100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-8px)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.6s cubic-bezier(0.16,1,0.3,1) both",
        float: "float 6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
