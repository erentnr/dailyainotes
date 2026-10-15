import { useEffect, useState } from "react";

import { Contrast } from "../components/ui/Icons";

/** Light or dark; the choice is kept in the browser and otherwise follows the system. */
export default function ThemeToggle({ className = "icon-button" }: { className?: string }) {
  const [dark, setDark] = useState(false);
  useEffect(() => setDark(document.documentElement.classList.contains("dark")), []);
  const toggle = () => {
    const next = !dark;
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("dan.theme", next ? "dark" : "light");
    setDark(next);
  };
  return (
    <button
      type="button"
      className={className}
      onClick={toggle}
      aria-label={dark ? "Use the light theme" : "Use the dark theme"}
    >
      <Contrast />
    </button>
  );
}
