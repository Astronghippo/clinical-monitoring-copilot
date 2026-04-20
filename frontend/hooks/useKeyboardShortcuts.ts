import { useEffect } from "react";
import type { Finding } from "@/lib/types";

interface UseKeyboardShortcutsOptions {
  findings: Finding[];
  selectedIndex: number;
  onSelectIndex: (index: number) => void;
  onOpenFinding: (finding: Finding) => void;
  onExport: () => void;
  searchInputRef: React.RefObject<HTMLInputElement>;
}

const GUARDED_TAGS = new Set(["INPUT", "TEXTAREA", "SELECT"]);

export function useKeyboardShortcuts({
  findings,
  selectedIndex,
  onSelectIndex,
  onOpenFinding,
  onExport,
  searchInputRef,
}: UseKeyboardShortcutsOptions): void {
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const tagName = target?.tagName ?? "";
      const isInField = GUARDED_TAGS.has(tagName);

      // "/" should focus search even when focus is in another field
      if (event.key === "/") {
        event.preventDefault();
        searchInputRef.current?.focus();
        return;
      }

      // Skip all other shortcuts when focus is inside an input/textarea/select
      if (isInField) return;

      switch (event.key) {
        case "j": {
          event.preventDefault();
          const next = Math.min(selectedIndex + 1, findings.length - 1);
          onSelectIndex(next);
          break;
        }
        case "k": {
          event.preventDefault();
          const prev = Math.max(selectedIndex - 1, 0);
          onSelectIndex(prev);
          break;
        }
        case "Enter": {
          event.preventDefault();
          const finding = findings[selectedIndex];
          if (finding !== undefined) {
            onOpenFinding(finding);
          }
          break;
        }
        case "e": {
          onExport();
          break;
        }
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [findings, selectedIndex, onSelectIndex, onOpenFinding, onExport, searchInputRef]);
}
