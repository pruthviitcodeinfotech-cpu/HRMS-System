import { create } from "zustand";
import { persist } from "zustand/middleware";

interface UserPreferenceState {
  pageSize: number;
  soundEnabled: boolean;
  viewMode: "grid" | "list";
  language: string;
  setPageSize: (pageSize: number) => void;
  setSoundEnabled: (enabled: boolean) => void;
  setViewMode: (mode: "grid" | "list") => void;
  setLanguage: (lang: string) => void;
}

export const useUserPreferenceStore = create<UserPreferenceState>()(
  persist(
    (set) => ({
      pageSize: 20,
      soundEnabled: true,
      viewMode: "grid",
      language: "en",
      setPageSize: (pageSize) => set({ pageSize }),
      setSoundEnabled: (soundEnabled) => set({ soundEnabled }),
      setViewMode: (viewMode) => set({ viewMode }),
      setLanguage: (language) => set({ language }),
    }),
    {
      name: "hrms-user-preferences",
    }
  )
);
