/** Tailwind theme = design/design_guidelines.json tokens, mapped 1:1.
 * The "band" colors are the core motif — color is functional only.
 * Numbers come straight from the committed design system so every surface
 * shares one visual language. */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Surfaces & ink (design §1)
        bg: "#f4f5f7",
        card: "#ffffff",
        raised: "#f7f8fa",
        ink: "#14161a",
        ink2: "#5b6472",
        ink3: "#8a93a0",
        ink4: "#9aa2ae",
        inkDisabled: "#b6bdc7",
        hairline: "#e7e9ee",
        hairline2: "#eef0f3",
        hairline3: "#f4f5f7",
        // Functional bands — green/orange/red/gray/blue. fg = text-on-white;
        // the *bg/*border variants are the tinted chip/backdrop.
        // green — bullish / pass / allowed
        bull: "#0f7a3d",
        "bull-bg": "#e6f6ec",
        "bull-border": "#c2e6cf",
        "bull-dot": "#22c55e",
        // orange — extreme-bullish / caution
        warn: "#9a5b00",
        "warn-bg": "#fdf0dd",
        "warn-border": "#f1d7a6",
        "warn-dot": "#f6a609",
        // red — bearish / fail / off
        bear: "#b42318",
        "bear-bg": "#fdecea",
        "bear-border": "#f4c9c4",
        "bear-dot": "#e5484d",
        // gray — neutral
        muted: "#5b6472",
        "muted-bg": "#f0f1f4",
        "muted-border": "#e2e5ea",
        "muted-dot": "#9aa2ae",
        // blue — secondary highlight
        info: "#175cd3",
        "info-bg": "#e9f1fd",
        "info-border": "#c7dbf7",
        "info-dot": "#4a90ff",
        // saffron / purpledot carried over from legacy palette
        saffron: "#f59e0b",
        purpledot: "#7c3aed",
      },
      fontFamily: {
        // Mono-forward; JetBrains Mono is the ship-bundled choice (design §2).
        mono: [
          "'JetBrains Mono'", "'Cascadia Code'", "'Cascadia Mono'",
          "'IBM Plex Mono'", "ui-monospace", "Consolas", "monospace",
        ],
        sans: ["system-ui", "'Segoe UI Variable'", "'Segoe UI'", "sans-serif"],
      },
      borderRadius: {
        chip: "5px",
        "chip-lg": "7px",
        btn: "8px",
        card: "12px",
        "card-lg": "14px",
      },
      letterSpacing: {
        overline: "0.06em",
      },
      maxWidth: {
        content: "1440px",
      },
    },
  },
  plugins: [],
};
