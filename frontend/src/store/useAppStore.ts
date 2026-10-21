import { create } from "zustand";
import {
  generateVideo,
  getBarometro,
  getEmpresas,
  getKpis,
  getVideoInfo,
  postChat,
} from "@/services/api";
import type {
  BarometroResumen,
  ChatMessage,
  EmpresaScore,
  Kpis,
  VideoInfo,
  VideoResult,
} from "@/services/types";

interface AppState {
  kpis: Kpis | null;
  barometro: BarometroResumen | null;
  loading: boolean;
  error: string | null;

  empresas: EmpresaScore[];
  empresasLoading: boolean;

  chat: ChatMessage[];
  chatLoading: boolean;

  video: VideoResult | null;
  videoInfo: VideoInfo | null;
  videoLoading: boolean;
  videoError: string | null;

  loadHome: () => Promise<void>;
  loadEmpresas: (periodo?: string) => Promise<void>;
  sendChat: (text: string) => Promise<void>;
  resetChat: () => void;
  loadVideoInfo: () => Promise<void>;
  generateVideo: () => Promise<void>;
}

export const useAppStore = create<AppState>((set) => ({
  kpis: null,
  barometro: null,
  loading: false,
  error: null,

  empresas: [],
  empresasLoading: false,

  chat: [],
  chatLoading: false,

  video: null,
  videoInfo: null,
  videoLoading: false,
  videoError: null,

  loadHome: async () => {
    set({ loading: true, error: null });
    try {
      const [kpis, barometro] = await Promise.all([getKpis(), getBarometro()]);
      set({ kpis, barometro, loading: false });
    } catch (e) {
      set({
        error: e instanceof Error ? e.message : "Error al cargar el barómetro",
        loading: false,
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

  resetChat: () => set({ chat: [] }),

  loadVideoInfo: async () => {
    try {
      const videoInfo = await getVideoInfo();
      set({ videoInfo });
    } catch {
      // la API no está disponible; se ignora
    }
  },

  generateVideo: async () => {
    set({ videoLoading: true, videoError: null });
    try {
      const video = await generateVideo();
      const videoInfo = await getVideoInfo();
      set({ video, videoInfo, videoLoading: false });
    } catch (e) {
      set({
        videoError: e instanceof Error ? e.message : "Error al generar el video",
        videoLoading: false,
      });
    }
  },
}));
