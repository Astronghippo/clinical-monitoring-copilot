import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { useRef } from "react";
import { useKeyboardShortcuts } from "../useKeyboardShortcuts";
import type { Finding } from "../../lib/types";

function makeFinding(id: number): Finding {
  return {
    id,
    analyzer: "visit_windows",
    severity: "major",
    subject_id: `subj-${id}`,
    summary: `Finding ${id}`,
    detail: "details",
    protocol_citation: "§1",
    data_citation: {},
    confidence: 1.0,
    status: "open",
    assignee: null,
    notes: null,
    updated_at: null,
  };
}

function fireKey(
  key: string,
  target?: EventTarget,
  modifiers?: { ctrlKey?: boolean; metaKey?: boolean; altKey?: boolean },
) {
  const event = new KeyboardEvent("keydown", { key, bubbles: true, ...modifiers });
  if (target) {
    Object.defineProperty(event, "target", { value: target });
  }
  window.dispatchEvent(event);
}

describe("useKeyboardShortcuts", () => {
  const findings = [makeFinding(1), makeFinding(2), makeFinding(3)];
  let onSelectIndex: ReturnType<typeof vi.fn>;
  let onOpenFinding: ReturnType<typeof vi.fn>;
  let onExport: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onSelectIndex = vi.fn();
    onOpenFinding = vi.fn();
    onExport = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("j increments selectedIndex and clamps at findings.length - 1", () => {
    const { rerender } = renderHook(
      ({ idx }: { idx: number }) =>
        useKeyboardShortcuts({
          findings,
          selectedIndex: idx,
          onSelectIndex,
          onOpenFinding,
          onExport,
          searchInputRef: { current: null },
        }),
      { initialProps: { idx: 1 } },
    );

    fireKey("j");
    expect(onSelectIndex).toHaveBeenCalledWith(2);

    onSelectIndex.mockClear();
    rerender({ idx: 2 });
    fireKey("j");
    // should clamp at 2 (findings.length - 1)
    expect(onSelectIndex).toHaveBeenCalledWith(2);
  });

  it("k decrements selectedIndex and clamps at 0", () => {
    const { rerender } = renderHook(
      ({ idx }: { idx: number }) =>
        useKeyboardShortcuts({
          findings,
          selectedIndex: idx,
          onSelectIndex,
          onOpenFinding,
          onExport,
          searchInputRef: { current: null },
        }),
      { initialProps: { idx: 1 } },
    );

    fireKey("k");
    expect(onSelectIndex).toHaveBeenCalledWith(0);

    onSelectIndex.mockClear();
    rerender({ idx: 0 });
    fireKey("k");
    // should clamp at 0
    expect(onSelectIndex).toHaveBeenCalledWith(0);
  });

  it("Enter calls onOpenFinding with the finding at selectedIndex", () => {
    renderHook(() =>
      useKeyboardShortcuts({
        findings,
        selectedIndex: 1,
        onSelectIndex,
        onOpenFinding,
        onExport,
        searchInputRef: { current: null },
      }),
    );

    fireKey("Enter");
    expect(onOpenFinding).toHaveBeenCalledWith(findings[1]);
  });

  it("Enter does nothing when selectedIndex is out of bounds", () => {
    renderHook(() =>
      useKeyboardShortcuts({
        findings,
        selectedIndex: -1,
        onSelectIndex,
        onOpenFinding,
        onExport,
        searchInputRef: { current: null },
      }),
    );

    fireKey("Enter");
    expect(onOpenFinding).not.toHaveBeenCalled();
  });

  it("e calls onExport", () => {
    renderHook(() =>
      useKeyboardShortcuts({
        findings,
        selectedIndex: 0,
        onSelectIndex,
        onOpenFinding,
        onExport,
        searchInputRef: { current: null },
      }),
    );

    fireKey("e");
    expect(onExport).toHaveBeenCalledTimes(1);
  });

  it("/ focuses the search input", () => {
    const input = document.createElement("input");
    const focusSpy = vi.spyOn(input, "focus");
    const ref = { current: input };

    renderHook(() =>
      useKeyboardShortcuts({
        findings,
        selectedIndex: 0,
        onSelectIndex,
        onOpenFinding,
        onExport,
        searchInputRef: ref,
      }),
    );

    fireKey("/");
    expect(focusSpy).toHaveBeenCalledTimes(1);
  });

  it("does not fire shortcuts when focus is on an INPUT element", () => {
    renderHook(() =>
      useKeyboardShortcuts({
        findings,
        selectedIndex: 0,
        onSelectIndex,
        onOpenFinding,
        onExport,
        searchInputRef: { current: null },
      }),
    );

    const input = document.createElement("input");
    document.body.appendChild(input);
    input.focus();
    const event = new KeyboardEvent("keydown", { key: "j", bubbles: true });
    Object.defineProperty(event, "target", { value: input });
    window.dispatchEvent(event);
    document.body.removeChild(input);

    expect(onSelectIndex).not.toHaveBeenCalled();
  });

  it("does not fire shortcuts when focus is on a TEXTAREA element", () => {
    renderHook(() =>
      useKeyboardShortcuts({
        findings,
        selectedIndex: 0,
        onSelectIndex,
        onOpenFinding,
        onExport,
        searchInputRef: { current: null },
      }),
    );

    const textarea = document.createElement("textarea");
    document.body.appendChild(textarea);
    const event = new KeyboardEvent("keydown", { key: "e", bubbles: true });
    Object.defineProperty(event, "target", { value: textarea });
    window.dispatchEvent(event);
    document.body.removeChild(textarea);

    expect(onExport).not.toHaveBeenCalled();
  });

  it("does not fire shortcuts when focus is on a SELECT element", () => {
    renderHook(() =>
      useKeyboardShortcuts({
        findings,
        selectedIndex: 0,
        onSelectIndex,
        onOpenFinding,
        onExport,
        searchInputRef: { current: null },
      }),
    );

    const select = document.createElement("select");
    document.body.appendChild(select);
    const event = new KeyboardEvent("keydown", { key: "k", bubbles: true });
    Object.defineProperty(event, "target", { value: select });
    window.dispatchEvent(event);
    document.body.removeChild(select);

    expect(onSelectIndex).not.toHaveBeenCalled();
  });

  it("/ still focuses search even when called from an input context (it bypasses guard)", () => {
    const input = document.createElement("input");
    const searchInput = document.createElement("input");
    const focusSpy = vi.spyOn(searchInput, "focus");
    document.body.appendChild(input);
    document.body.appendChild(searchInput);

    renderHook(() =>
      useKeyboardShortcuts({
        findings,
        selectedIndex: 0,
        onSelectIndex,
        onOpenFinding,
        onExport,
        searchInputRef: { current: searchInput },
      }),
    );

    // Fire / with target being an input — should still focus search
    const event = new KeyboardEvent("keydown", { key: "/", bubbles: true });
    Object.defineProperty(event, "target", { value: input });
    window.dispatchEvent(event);

    expect(focusSpy).toHaveBeenCalledTimes(1);
    document.body.removeChild(input);
    document.body.removeChild(searchInput);
  });

  it("does not fire j shortcut when ctrlKey is held", () => {
    renderHook(() =>
      useKeyboardShortcuts({
        findings,
        selectedIndex: 0,
        onSelectIndex,
        onOpenFinding,
        onExport,
        searchInputRef: { current: null },
      }),
    );

    fireKey("j", undefined, { ctrlKey: true });
    expect(onSelectIndex).not.toHaveBeenCalled();
  });

  it("does not fire j shortcut when metaKey is held", () => {
    renderHook(() =>
      useKeyboardShortcuts({
        findings,
        selectedIndex: 0,
        onSelectIndex,
        onOpenFinding,
        onExport,
        searchInputRef: { current: null },
      }),
    );

    fireKey("j", undefined, { metaKey: true });
    expect(onSelectIndex).not.toHaveBeenCalled();
  });

  it("does not fire j shortcut when altKey is held", () => {
    renderHook(() =>
      useKeyboardShortcuts({
        findings,
        selectedIndex: 0,
        onSelectIndex,
        onOpenFinding,
        onExport,
        searchInputRef: { current: null },
      }),
    );

    fireKey("j", undefined, { altKey: true });
    expect(onSelectIndex).not.toHaveBeenCalled();
  });

  it("does not focus search when / is pressed with ctrlKey held", () => {
    const input = document.createElement("input");
    const focusSpy = vi.spyOn(input, "focus");
    const ref = { current: input };

    renderHook(() =>
      useKeyboardShortcuts({
        findings,
        selectedIndex: 0,
        onSelectIndex,
        onOpenFinding,
        onExport,
        searchInputRef: ref,
      }),
    );

    fireKey("/", undefined, { ctrlKey: true });
    expect(focusSpy).not.toHaveBeenCalled();
  });

  it("cleans up event listener on unmount", () => {
    const removeEventListenerSpy = vi.spyOn(window, "removeEventListener");

    const { unmount } = renderHook(() =>
      useKeyboardShortcuts({
        findings,
        selectedIndex: 0,
        onSelectIndex,
        onOpenFinding,
        onExport,
        searchInputRef: { current: null },
      }),
    );

    unmount();
    expect(removeEventListenerSpy).toHaveBeenCalledWith(
      "keydown",
      expect.any(Function),
    );
  });
});
