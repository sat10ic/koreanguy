/** Light-terminal design tokens. Western semantics: green = up/bull, red = down/bear.
 * Semantic names (bull/bear/warn/info/muted) stay stable so all logic reads the same;
 * only the color values differ from the old app. */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Surfaces & ink — light terminal canvas
        bg: "#eef1f4",
        card: "#ffffff",
        raised: "#f6f8fa",
        ink: "#14181d",
        ink2: "#4a5560",
        ink3: "#7a8590",
        ink4: "#9aa3ad",
        inkDisabled: "#b6bdc6",
        hairline: "#d9dfe6",
        hairline2: "#e6ebf0",
        hairline3: "#f0f3f6",
        // Functional bands — Western: green = up/bull, red = down/bear
        bull: "#0f7a3d",
        "bull-bg": "#e6f6ec",
        "bull-border": "#c2e6cf",
        "bull-dot": "#22c55e",
        warn: "#9a5b00",
        "warn-bg": "#fdf0dd",
        "warn-border": "#f1d7a6",
        "warn-dot": "#f6a609",
        bear: "#b42318",
        "bear-bg": "#fdecea",
        "bear-border": "#f4c9c4",
        "bear-dot": "#e5484d",
        muted: "#5b6472",
        "muted-bg": "#f0f1f4",
        "muted-border": "#e2e5ea",
        "muted-dot": "#9aa2ae",
        info: "#175cd3",
        "info-bg": "#e9f1fd",
        "info-border": "#c7dbf7",
        "info-dot": "#4a90ff",
      },
      fontFamily: {
        mono: ["'JetBrains Mono'", "ui-monospace", "Consolas", "monospace"],
        sans: ["'Archivo'", "system-ui", "'Segoe UI'", "sans-serif"],
      },
      fontSize: {
        "2xs": ["10px", "14px"],
        xs: ["11px", "16px"],
        sm: ["12px", "18px"],
        base: ["13px", "20px"],
      },
      borderRadius: {
        chip: "4px",
        panel: "6px",
      },
      letterSpacing: {
        overline: "0.08em",
      },
      maxWidth: {
        content: "1600px",
      },
    },
  },
  plugins: [],
};