import { create } from "zustand";
import { createStoreWithDevtools } from "./store-utils";

interface GlobalState {
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
}

export const useGlobalStore = create<GlobalState>()(
  createStoreWithDevtools(
    (set) => ({
      sidebarOpen: true,
      setSidebarOpen: (open) => set({ sidebarOpen: open }, false, "setSidebarOpen"),
    }),
    "GlobalStore"
  )
);
