import { render, screen } from "@testing-library/react";
import { Button } from "./button";
import { expect, test, describe } from "vitest";

describe("Button Component", () => {
  test("renders button with correct text", () => {
    render(<Button>Click Me</Button>);
    expect(screen.getByRole("button", { name: /click me/i })).toBeInTheDocument();
  });

  test("applies primary class by default", () => {
    render(<Button>Click Me</Button>);
    const button = screen.getByRole("button", { name: /click me/i });
    expect(button.className).toContain("bg-primary");
  });

  test("applies variant classes correctly", () => {
    render(<Button variant="destructive">Delete</Button>);
    const button = screen.getByRole("button", { name: /delete/i });
    expect(button.className).toContain("bg-[hsl(346.8,77.2%,49.8%)]");
  });
});
