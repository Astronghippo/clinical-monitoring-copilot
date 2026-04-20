"use client";
import { useEffect, useState } from "react";

const STORAGE_KEY = "dark-mode";

function applyDark(isDark: boolean) {
  if (isDark) {
    document.documentElement.classList.add("dark");
  } else {
    document.documentElement.classList.remove("dark");
  }
}

export function useDarkMode() {
  const [isDark, setIsDark] = useState<boolean>(() => {
    // On server-side (SSR) or during static generation there is no window.
    if (typeof window === "undefined") return false;

    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored !== null) return stored === "true";

    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  });

  // Apply the class immediately when the component mounts (and on changes).
  useEffect(() => {
    applyDark(isDark);
  }, [isDark]);

  // Listen for OS-level changes when localStorage has no override.
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = (e: MediaQueryListEvent) => {
      // Only respond to OS changes when the user has not set a manual preference.
      if (localStorage.getItem(STORAGE_KEY) === null) {
        setIsDark(e.matches);
      }
    };
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  function toggle() {
    setIsDark((prev) => {
      const next = !prev;
      localStorage.setItem(STORAGE_KEY, String(next));
      applyDark(next);
      return next;
    });
  }

  return { isDark, toggle };
}
