module.exports = {
  darkMode: "class",
  content: [
    "./pages/**/*.html",
    "./partials/**/*.html"
  ],
  safelist: [
    "px-3",
    "py-1.5",
    "rounded-full",
    "bg-primary/10",
    "text-primary",
    "font-semibold",
    "hover:bg-slate-100",
    "transition-colors",
    "sm:px-4",
    "py-2",
    "rounded-xl",
    "bg-primary",
    "text-white",
    "text-[13px]",
    "sm:text-sm",
    "whitespace-nowrap"
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
