import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    // severity/risk color classes are defined as literals here:
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Soft pistachio palette — the app's signature light theme.
        pistachio: {
          50: "#f6faef",
          100: "#eaf4d9",
          200: "#dcedc1", // page background
          300: "#c6e1a0",
          400: "#aad177",
          500: "#8fbd57",
          600: "#74a03f", // accent
          700: "#5b7e34",
          800: "#48632c",
          900: "#3c5228",
        },
        // Near-black with a faint green cast, for body text/headings.
        ink: "#16230d",
      },
      boxShadow: {
        soft: "0 1px 2px rgba(20,40,15,0.05), 0 10px 30px -12px rgba(20,40,15,0.18)",
      },
    },
  },
  plugins: [],
};

export default config;
