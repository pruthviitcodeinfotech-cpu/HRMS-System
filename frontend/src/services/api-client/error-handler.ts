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
        const msg = typeof errorData.message === "string" ? errorData.message : "";
        const detail = typeof errorData.detail === "string" ? errorData.detail : "";
        errorResponse.message = msg || detail || axiosError.message || errorResponse.message;
        errorResponse.code = typeof errorData.code === "string" ? errorData.code : undefined;
        errorResponse.errors = errorData.errors as Record<string, string[]> | undefined;
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
