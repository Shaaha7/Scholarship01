// lib/auth-store.ts
import { create } from "zustand";
import { persist } from "zustand/middleware";
import Cookies from "js-cookie";
import { apiClient } from "./api-client";

interface User {
  id: string;
  email: string;
  full_name?: string;
  role: string;
  preferred_language: string;
  profile_data?: Record<string, any>;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  loadUser: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,

      login: async (email, password) => {
        const res = await apiClient.post("/auth/login", { email, password });
        const { access_token, refresh_token } = res.data;
        Cookies.set("access_token", access_token, { secure: true, sameSite: "strict", expires: 1 });
        Cookies.set("refresh_token", refresh_token, { secure: true, sameSite: "strict", expires: 7 });
        await get().loadUser();
      },

      logout: async () => {
        try {
          const rt = Cookies.get("refresh_token");
          if (rt) await apiClient.post("/auth/logout", { refresh_token: rt });
        } catch {}
        Cookies.remove("access_token");
        Cookies.remove("refresh_token");
        set({ user: null, isAuthenticated: false });
      },

      loadUser: async () => {
        try {
          const res = await apiClient.get("/auth/me");
          set({ user: res.data, isAuthenticated: true });
        } catch {
          set({ user: null, isAuthenticated: false });
        }
      },
    }),
    { name: "tamilscholar-auth", partialize: (s) => ({ user: s.user, isAuthenticated: s.isAuthenticated }) }
  )
);

// lib/utils.ts
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatINR(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function getDaysUntil(date: string | Date): number {
  const d = new Date(date);
  const now = new Date();
  return Math.ceil((d.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
}
