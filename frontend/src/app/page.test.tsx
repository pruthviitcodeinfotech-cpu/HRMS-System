import { render, screen } from "@testing-library/react";
import Home from "./page";
import { expect, test } from "vitest";

test("renders page header and confirm setup text", () => {
  render(<Home />);
  expect(screen.getByText("HRMS Project Initialized")).toBeInTheDocument();
});
