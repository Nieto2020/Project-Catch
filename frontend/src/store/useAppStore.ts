import { create } from "zustand";
import {
  getBarometro,
  getDashboard,
  getEmpresas,
  postChat,
  postWhatif,
  type WhatIfPayload,
} from "@/services/api";
import type {
  BarometroResumen,
  ChatMessage,
  DashboardData,
  EmpresaScore,
  WhatIfResult,
} from "@/services/types";

interface AppState {
  dashboard: DashboardData | null;
  dashboardLoading: boolean;
  dashboardError: string | null;

  barometro: BarometroResumen | null;
  empresas: EmpresaScore[];
  empresasLoading: boolean;

  chat: ChatMessage[];
  chatLoading: boolean;

  whatif: WhatIfResult | null;
  whatifLoading: boolean;
  whatifError: string | null;

  loadDashboard: () => Promise<void>;
  loadEmpresas: (periodo?: string) => Promise<void>;
  sendChat: (text: string) => Promise<void>;
  runWhatif: (payload: WhatIfPayload) => Promise<void>;
  resetChat: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  dashboard: null,
  dashboardLoading: false,
  dashboardError: null,

  barometro: null,
  empresas: [],
  empresasLoading: false,

  chat: [],
  chatLoading: false,

  whatif: null,
  whatifLoading: false,
  whatifError: null,

  loadDashboard: async () => {
    set({ dashboardLoading: true, dashboardError: null });
    try {
      const [dashboard, barometro] = await Promise.all([
        getDashboard(),
        getBarometro(),
      ]);
      set({ dashboard, barometro, dashboardLoading: false });
    } catch (e) {
      set({
        dashboardError: e instanceof Error ? e.message : "Error al cargar el dashboard",
        dashboardLoading: false,
      });
    }
  },

  loadEmpresas: async (periodo) => {
    set({ empresasLoading: true });
    try {
      const empresas = await getEmpresas(periodo);
      set({ empresas, empresasLoading: false });
    } catch {
      set({ empresasLoading: false });
    }
  },

  sendChat: async (text) => {
    const userMsg: ChatMessage = { role: "user", content: text };
    set((s) => ({ chat: [...s.chat, userMsg], chatLoading: true }));
    try {
      const res = await postChat(text);
      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: res.answer,
        engine: res.engine,
      };
      set((s) => ({ chat: [...s.chat, assistantMsg], chatLoading: false }));
    } catch (e) {
      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: `No pude conectar con la API: ${e instanceof Error ? e.message : "error"}`,
      };
      set((s) => ({ chat: [...s.chat, assistantMsg], chatLoading: false }));
    }
  },

  runWhatif: async (payload) => {
    set({ whatifLoading: true, whatifError: null });
    try {
      const whatif = await postWhatif(payload);
      set({ whatif, whatifLoading: false });
    } catch (e) {
      set({
        whatifError: e instanceof Error ? e.message : "Error en la simulación",
        whatifLoading: false,
      });
    }
  },

  resetChat: () => set({ chat: [] }),
}));
