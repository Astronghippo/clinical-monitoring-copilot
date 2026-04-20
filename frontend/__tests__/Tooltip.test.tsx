import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Tooltip } from "../components/Tooltip";

describe("Tooltip", () => {
  it("renders children", () => {
    render(
      <Tooltip text="Help text">
        <button>Click me</button>
      </Tooltip>
    );
    expect(screen.getByRole("button", { name: "Click me" })).toBeInTheDocument();
  });

  it("renders tooltip text", () => {
    render(
      <Tooltip text="Help text">
        <button>Click me</button>
      </Tooltip>
    );
    expect(screen.getByRole("tooltip")).toBeInTheDocument();
    expect(screen.getByRole("tooltip")).toHaveTextContent("Help text");
  });

  it("tooltip is hidden by default via opacity-0 class", () => {
    render(
      <Tooltip text="Hidden tooltip">
        <span>Hover me</span>
      </Tooltip>
    );
    const tooltip = screen.getByRole("tooltip");
    expect(tooltip.className).toContain("opacity-0");
  });

  it("tooltip has role='tooltip'", () => {
    render(
      <Tooltip text="Accessible tooltip">
        <span>Target</span>
      </Tooltip>
    );
    expect(screen.getByRole("tooltip")).toBeInTheDocument();
  });

  it("trigger has aria-describedby pointing to tooltip id", () => {
    render(
      <Tooltip text="Described by this">
        <button>Trigger</button>
      </Tooltip>
    );
    const tooltip = screen.getByRole("tooltip");
    const tooltipId = tooltip.id;
    expect(tooltipId).toBeTruthy();

    const button = screen.getByRole("button", { name: "Trigger" });
    expect(button).toHaveAttribute("aria-describedby", tooltipId);
  });

  it("tooltip is visible when trigger is focused", () => {
    render(
      <Tooltip text="Focus tooltip">
        <button>Focus me</button>
      </Tooltip>
    );
    const button = screen.getByRole("button", { name: "Focus me" });
    button.focus();
    const tooltip = screen.getByRole("tooltip");
    expect(tooltip.className).toContain("group-focus-within:opacity-100");
  });
});
