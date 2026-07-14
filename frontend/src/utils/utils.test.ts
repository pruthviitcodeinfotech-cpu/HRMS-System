import { formatCurrency, capitalize } from "./formatters";
import { formatDate, getDaysInMonth } from "./date";
import { isValidEmail, isNumeric, isValidIndianMobile } from "./validators";
import { expect, test, describe } from "vitest";

describe("Formatters Utility", () => {
  test("formatCurrency formats correctly to INR", () => {
    const formatted = formatCurrency(123456.78);
    expect(formatted).toContain("1,23,456.78");
  });

  test("capitalize capitalizes string correctly", () => {
    expect(capitalize("hello WORLD")).toBe("Hello world");
  });
});

describe("Date Utility", () => {
  test("formatDate parses and formats correctly", () => {
    expect(formatDate("2026-07-14", "YYYY-MM-DD")).toBe("2026-07-14");
  });

  test("getDaysInMonth returns correct days count", () => {
    expect(getDaysInMonth(2026, 2)).toBe(28);
  });
});

describe("Validators Utility", () => {
  test("isValidEmail checks email pattern correctly", () => {
    expect(isValidEmail("test@example.com")).toBe(true);
    expect(isValidEmail("invalid-email")).toBe(false);
  });

  test("isNumeric checks digits only", () => {
    expect(isNumeric("12345")).toBe(true);
    expect(isNumeric("12a45")).toBe(false);
  });

  test("isValidIndianMobile checks phone format", () => {
    expect(isValidIndianMobile("9876543210")).toBe(true);
    expect(isValidIndianMobile("1234567890")).toBe(false);
  });
});
