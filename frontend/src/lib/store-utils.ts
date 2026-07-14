import { StateCreator } from "zustand";
import { devtools } from "zustand/middleware";

// Helper to define devtools middleware cleanly in TypeScript
export const createStoreWithDevtools = <T extends object>(
  initializer: StateCreator<T, [["zustand/devtools", never]], []>,
  name: string
) => {
  return devtools(initializer, { name });
};
