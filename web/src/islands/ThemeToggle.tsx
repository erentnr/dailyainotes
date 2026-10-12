import { useEffect, useState } from "react";

import { Moon, Sun } from "../components/ui/Icons";

/** Light · Paper or Dark · Carbon; the choice is kept in the browser. */
export default function ThemeToggle() {
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
      className="icon-button"
      onClick={toggle}
      aria-label={dark ? "Use the light theme" : "Use the dark theme"}
    >
      {dark ? <Sun /> : <Moon />}
    </button>
  );
}
