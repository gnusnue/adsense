module.exports = {
  darkMode: "class",
  content: [
    "./pages/**/*.html",
    "./partials/**/*.html"
  ],
  safelist: [
    "ds-nav-link",
    "ds-nav-link-active",
    "ds-nav-link-inactive",
    "ds-tab-link",
    "ds-tab-link-active",
    "ds-tab-link-inactive"
  ],
  theme: {
    extend: {
      colors: {
        primary: "#1c74e9",
        "background-light": "#f6f7f8",
        "background-dark": "#111821"
      },
      fontFamily: {
        display: ["Public Sans", "sans-serif"]
      },
      borderRadius: {
        DEFAULT: "0.25rem",
        lg: "0.5rem",
        xl: "0.75rem",
        full: "9999px"
      }
    }
  },
  plugins: [require("@tailwindcss/forms"), require("@tailwindcss/container-queries")]
};
