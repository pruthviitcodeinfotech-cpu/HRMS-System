/**
 * Type-safe environment variables config.
 * Note: Zod verification can be integrated once Zod is added.
 */

export const env = {
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  NODE_ENV: process.env.NODE_ENV || "development",
} as const;

// Validate environment on server-side startup
if (typeof window === "undefined") {
  const requiredEnv = ["NEXT_PUBLIC_API_URL"] as const;
  for (const key of requiredEnv) {
    if (!process.env[key]) {
      console.warn(
        `[Warning] Environment variable ${key} is missing in production/build environment.`
      );
    }
  }
}
