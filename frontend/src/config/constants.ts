export const APP_CONFIG = {
  name: "HRMS & Payroll System",
  shortName: "HRMS",
  defaultLanguage: "en",
  defaultPageSize: 20,
  maxPageSize: 100,
} as const;

export const API_ROUTES = {
  auth: {
    login: "/auth/login",
    logout: "/auth/logout",
    refresh: "/auth/refresh",
    me: "/auth/me",
  },
} as const;
