import { create } from "zustand";
import { createStoreWithDevtools } from "../store-utils";

interface UIState {
  pageTitle: string;
  activeModals: Record<string, boolean>;
  setPageTitle: (title: string) => void;
  openModal: (modalId: string) => void;
  closeModal: (modalId: string) => void;
  closeAllModals: () => void;
}

export const useUIStore = create<UIState>()(
  createStoreWithDevtools(
    (set) => ({
      pageTitle: "Dashboard",
      activeModals: {},
      setPageTitle: (title) => set({ pageTitle: title }, false, "setPageTitle"),
      openModal: (modalId) =>
        set(
          (state) => ({ activeModals: { ...state.activeModals, [modalId]: true } }),
          false,
          "openModal"
        ),
      closeModal: (modalId) =>
        set(
          (state) => ({ activeModals: { ...state.activeModals, [modalId]: false } }),
          false,
          "closeModal"
        ),
      closeAllModals: () => set({ activeModals: {} }, false, "closeAllModals"),
    }),
    "UIStore"
  )
);
