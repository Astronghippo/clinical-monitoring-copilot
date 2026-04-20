import { renderHook, act } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useDarkMode } from "../useDarkMode";

function mockMatchMedia(prefersDark: boolean) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: prefersDark && query === "(prefers-color-scheme: dark)",
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  });
}

// Build a minimal in-memory localStorage stand-in.
function makeLocalStorage() {
  const store: Record<string, string> = {};
  return {
    getItem: (key: string) => (key in store ? store[key] : null),
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { for (const k in store) delete store[k]; },
  };
}

describe("useDarkMode", () => {
  let fakeStorage: ReturnType<typeof makeLocalStorage>;

  beforeEach(() => {
    fakeStorage = makeLocalStorage();
    vi.stubGlobal("localStorage", fakeStorage);
    document.documentElement.classList.remove("dark");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    document.documentElement.classList.remove("dark");
  });

  it("detects prefers-color-scheme: dark from matchMedia → isDark is true", () => {
    mockMatchMedia(true);
    const { result } = renderHook(() => useDarkMode());
    expect(result.current.isDark).toBe(true);
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("no matchMedia match → isDark is false", () => {
    mockMatchMedia(false);
    const { result } = renderHook(() => useDarkMode());
    expect(result.current.isDark).toBe(false);
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("toggle flips isDark from false to true, updates classList and localStorage", () => {
    mockMatchMedia(false);
    const { result } = renderHook(() => useDarkMode());
    expect(result.current.isDark).toBe(false);

    act(() => {
      result.current.toggle();
    });

    expect(result.current.isDark).toBe(true);
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(fakeStorage.getItem("dark-mode")).toBe("true");
  });

  it("toggle flips isDark from true to false, updates classList and localStorage", () => {
    mockMatchMedia(true);
    const { result } = renderHook(() => useDarkMode());
    expect(result.current.isDark).toBe(true);

    act(() => {
      result.current.toggle();
    });

    expect(result.current.isDark).toBe(false);
    expect(document.documentElement.classList.contains("dark")).toBe(false);
    expect(fakeStorage.getItem("dark-mode")).toBe("false");
  });

  it("localStorage 'true' → isDark is true regardless of matchMedia", () => {
    mockMatchMedia(false); // matchMedia says light
    fakeStorage.setItem("dark-mode", "true");
    const { result } = renderHook(() => useDarkMode());
    expect(result.current.isDark).toBe(true);
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("localStorage 'false' → isDark is false regardless of matchMedia", () => {
    mockMatchMedia(true); // matchMedia says dark
    fakeStorage.setItem("dark-mode", "false");
    const { result } = renderHook(() => useDarkMode());
    expect(result.current.isDark).toBe(false);
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("removes matchMedia listener on unmount", () => {
    const removeEventListener = vi.fn();
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation((_query: string) => ({
        matches: false,
        addEventListener: vi.fn(),
        removeEventListener,
      })),
    });

    const { unmount } = renderHook(() => useDarkMode());
    unmount();
    expect(removeEventListener).toHaveBeenCalledWith("change", expect.any(Function));
  });
});
