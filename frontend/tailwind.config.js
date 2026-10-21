/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: "#F5F0E7",
        sand: "#EAE2D5",
        surface: "#FFFDF8",
        espresso: {
          DEFAULT: "#382B25",
          dark: "#241B17",
          light: "#4E3C34",
        },
        muted: "#786A5E",
        terracotta: {
          DEFAULT: "#B86E4B",
          dark: "#995636",
          light: "#CE8764",
        },
        sage: {
          DEFAULT: "#84927A",
          dark: "#697660",
          light: "#A1AEA7",
        },
        taupe: {
          DEFAULT: "#D7CCBD",
          dark: "#B8AC9C",
          light: "#E8E0D5",
        },
        forest: "#3D6E50",
        ochre: "#C28B38",
        brick: "#A94438",
      },
      fontFamily: {
        serif: ["Newsreader", "Georgia", "serif"],
        sans: ["'Plus Jakarta Sans'", "-apple-system", "BlinkMacSystemFont", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
        pixel: ["'Press Start 2P'", "monospace"],
      },
      boxShadow: {
        sm: "0 1px 2px rgba(56, 43, 37, 0.05)",
        DEFAULT: "0 1px 3px rgba(56, 43, 37, 0.08), 0 1px 2px rgba(56, 43, 37, 0.04)",
        md: "0 4px 6px -1px rgba(56, 43, 37, 0.08), 0 2px 4px -1px rgba(56, 43, 37, 0.04)",
      },
    },
  },
  plugins: [],
};
