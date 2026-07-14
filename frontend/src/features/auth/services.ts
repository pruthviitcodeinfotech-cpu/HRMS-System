import axios from "axios";
import { env } from "@/config/env";

export const refreshSession = async (): Promise<{ access_token: string }> => {
  const response = await axios.post<{ access_token: string }>(
    `${env.NEXT_PUBLIC_API_URL}/auth/refresh`,
    {},
    { withCredentials: true }
  );
  return response.data;
};

export const logoutSession = async (): Promise<void> => {
  await axios.post(`${env.NEXT_PUBLIC_API_URL}/auth/logout`, {}, { withCredentials: true });
};
