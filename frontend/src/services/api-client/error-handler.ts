import { AxiosError } from "axios";

export interface ApiErrorResponse {
  message: string;
  statusCode?: number;
  code?: string;
  errors?: Record<string, string[]>;
}

export class ApiError extends Error {
  public statusCode?: number;
  public code?: string;
  public errors?: Record<string, string[]>;

  constructor(response: ApiErrorResponse) {
    super(response.message);
    this.name = "ApiError";
    this.statusCode = response.statusCode;
    this.code = response.code;
    this.errors = response.errors;
  }
}

export const handleApiError = (error: unknown): ApiError => {
  if (error instanceof ApiError) {
    return error;
  }

  const errorResponse: ApiErrorResponse = {
    message: "An unexpected network or system error occurred.",
  };

  if (error && typeof error === "object") {
    // Check if it matches AxiosError signature
    const axiosError = error as AxiosError<unknown>;
    if (axiosError.isAxiosError || axiosError.response || axiosError.request) {
      errorResponse.statusCode = axiosError.response?.status;

      const data = axiosError.response?.data;
      if (data && typeof data === "object") {
        const errorData = data as Record<string, unknown>;

        // 1. Support FastAPI Pydantic validation error array: { detail: [{ loc, msg, type }] }
        if (Array.isArray(errorData.detail)) {
          const formattedDetails = errorData.detail
            .map((err: unknown) => {
              if (err && typeof err === "object") {
                const e = err as Record<string, unknown>;
                const field = Array.isArray(e.loc) ? e.loc[e.loc.length - 1] : null;
                const msg = typeof e.msg === "string" ? e.msg : "Invalid field";
                return field ? `${field}: ${msg}` : msg;
              }
              return String(err);
            })
            .join("; ");
          errorResponse.message = formattedDetails || "Validation error occurred.";
        }
        // 2. Support standard nested backend ErrorResponse: { success: false, message, error: { code, message, details: [...] } }
        else if (errorData.error && typeof errorData.error === "object") {
          const nestedError = errorData.error as Record<string, unknown>;
          if (typeof nestedError.message === "string" && nestedError.message) {
            errorResponse.message = nestedError.message;
          }
          if (typeof nestedError.code === "string" && nestedError.code) {
            errorResponse.code = nestedError.code;
          }
          const details = nestedError.details;
          if (Array.isArray(details)) {
            const mappedErrors: Record<string, string[]> = {};
            for (const err of details) {
              if (err && typeof err === "object") {
                const errObj = err as Record<string, unknown>;
                const field = typeof errObj.field === "string" ? errObj.field : null;
                const message =
                  typeof errObj.message === "string" ? errObj.message : "Invalid value";
                if (field) {
                  if (!mappedErrors[field]) {
                    mappedErrors[field] = [];
                  }
                  mappedErrors[field].push(message);
                }
              }
            }
            errorResponse.errors = mappedErrors;
          }
        }
        // 3. Simple message or string detail
        else {
          const msg = typeof errorData.message === "string" ? errorData.message : "";
          const detail = typeof errorData.detail === "string" ? errorData.detail : "";
          errorResponse.message = msg || detail || axiosError.message || errorResponse.message;
          errorResponse.code = typeof errorData.code === "string" ? errorData.code : undefined;
        }
      } else {
        errorResponse.message = axiosError.message || errorResponse.message;
      }
    } else if (error instanceof Error) {
      errorResponse.message = error.message;
    }
  } else if (error instanceof Error) {
    errorResponse.message = error.message;
  }

  return new ApiError(errorResponse);
};
