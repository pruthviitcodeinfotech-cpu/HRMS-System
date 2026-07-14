import { handleApiError, ApiError } from "./error-handler";
import { buildQueryString } from "./utils";
import { expect, test, describe } from "vitest";

describe("API Error Handler", () => {
  test("returns generic ApiError for normal error object", () => {
    const error = new Error("Regular Error");
    const result = handleApiError(error);
    expect(result).toBeInstanceOf(ApiError);
    expect(result.message).toBe("Regular Error");
  });

  test("extracts details from mock AxiosError response data", () => {
    const mockAxiosError = {
      message: "Request failed",
      response: {
        status: 400,
        data: {
          message: "Validation failed",
          code: "VALIDATION_ERROR",
          errors: { email: ["Invalid email format"] },
        },
      },
    };
    const result = handleApiError(mockAxiosError);
    expect(result).toBeInstanceOf(ApiError);
    expect(result.statusCode).toBe(400);
    expect(result.message).toBe("Validation failed");
    expect(result.code).toBe("VALIDATION_ERROR");
    expect(result.errors).toEqual({ email: ["Invalid email format"] });
  });
});

describe("API Utilities", () => {
  test("buildQueryString formats object parameters correctly", () => {
    const params = { page: 1, limit: 10, q: "test", empty: null, undef: undefined };
    expect(buildQueryString(params)).toBe("?page=1&limit=10&q=test");
  });

  test("buildQueryString serializes array inputs correctly", () => {
    const params = { roles: ["admin", "user"] };
    expect(buildQueryString(params)).toBe("?roles=admin&roles=user");
  });

  test("buildQueryString returns empty string for empty inputs", () => {
    expect(buildQueryString({})).toBe("");
  });
});
