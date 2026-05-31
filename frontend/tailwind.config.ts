import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        ink: "#0e0e10",
        night: "#17151d",
        asphalt: "#25232b",
        rail: "#393642",
        paper: "#f3efe4",
        bone: "#fff8e8",
        acid: "#d6f84c",
        clyde: "#28b8a7",
        poster: "#ef4d2f",
        plum: "#7b4aa0",
        tenement: "#d987a1",
        amber: "#f6b33d"
      },
      fontFamily: {
        display: ["var(--font-display)", "Arial", "sans-serif"],
        sans: ["var(--font-sans)", "Arial", "sans-serif"],
        editorial: ["var(--font-editorial)", "Georgia", "serif"]
      },
      boxShadow: {
        poster: "0 24px 80px rgba(14, 14, 16, 0.38)",
        print: "8px 8px 0 rgba(14, 14, 16, 0.9)"
      }
    }
  },
  plugins: []
};

export default config;
