import { create } from "zustand";
import { createStoreWithDevtools } from "../store-utils";

interface SidebarState {
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
  toggle: () => void;
}

export const useSidebarStore = create<SidebarState>()(
  createStoreWithDevtools(
    (set) => ({
      isOpen: true,
      setIsOpen: (isOpen) => set({ isOpen }, false, "setIsOpen"),
      toggle: () => set((state) => ({ isOpen: !state.isOpen }), false, "toggle"),
    }),
    "SidebarStore"
  )
);
