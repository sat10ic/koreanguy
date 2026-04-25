/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}", "./public/index.html"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "monospace"],
      },
      colors: {
        page: "#050505",
        surface: "#121212",
        surfaceHover: "#1E1E1E",
        borderDefault: "#27272A",
        borderSubtle: "#18181B",
        textPrimary: "#F4F4F5",
        textSecondary: "#A1A1AA",
        textMuted: "#52525B",
        bull: "#10B981",
        bear: "#EF4444",
        warn: "#F59E0B",
        saffron: "#FF9933",
        purpledot: "#A855F7",
      },
      letterSpacing: {
        overline: "0.2em",
      },
    },
  },
  plugins: [],
};
