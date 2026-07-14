import { render } from "@testing-library/react";
import Home from "./page";
import { expect, test, vi } from "vitest";
import { redirect } from "next/navigation";

vi.mock("next/navigation", () => ({
  redirect: vi.fn(),
}));

test("redirects to dashboard", () => {
  render(<Home />);
  expect(redirect).toHaveBeenCalledWith("/dashboard");
});
