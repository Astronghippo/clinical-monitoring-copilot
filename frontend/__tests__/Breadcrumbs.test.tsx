import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

// Mock next/link to render a plain anchor so jsdom can inspect href
vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

import { Breadcrumbs } from "../components/Breadcrumbs";

describe("Breadcrumbs", () => {
  it("renders all item labels", () => {
    render(
      <Breadcrumbs
        items={[
          { label: "Home", href: "/" },
          { label: "Analyses", href: "/analyses" },
          { label: "Analysis #5" },
        ]}
      />,
    );
    expect(screen.getByText("Home")).toBeInTheDocument();
    expect(screen.getByText("Analyses")).toBeInTheDocument();
    expect(screen.getByText("Analysis #5")).toBeInTheDocument();
  });

  it("first item with href renders as a link", () => {
    render(
      <Breadcrumbs
        items={[
          { label: "Home", href: "/" },
          { label: "Analyses" },
        ]}
      />,
    );
    const link = screen.getByRole("link", { name: "Home" });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/");
  });

  it("last item renders as plain text (no link) and has aria-current='page'", () => {
    render(
      <Breadcrumbs
        items={[
          { label: "Home", href: "/" },
          { label: "Analyses", href: "/analyses" },
          { label: "Analysis #5" },
        ]}
      />,
    );
    // "Analysis #5" must not be a link
    const links = screen.getAllByRole("link");
    const linkTexts = links.map((l) => l.textContent);
    expect(linkTexts).not.toContain("Analysis #5");

    // It should carry aria-current="page"
    const currentEl = screen.getByText("Analysis #5");
    expect(currentEl).toHaveAttribute("aria-current", "page");
  });

  it("nav element has aria-label='breadcrumb'", () => {
    render(
      <Breadcrumbs
        items={[{ label: "Home", href: "/" }, { label: "Analyses" }]}
      />,
    );
    expect(screen.getByRole("navigation", { name: "breadcrumb" })).toBeInTheDocument();
  });

  it("single-item breadcrumb renders just the label with aria-current='page'", () => {
    render(<Breadcrumbs items={[{ label: "Home" }]} />);
    const el = screen.getByText("Home");
    expect(el).toHaveAttribute("aria-current", "page");
    expect(screen.queryByRole("link")).toBeNull();
  });
});
