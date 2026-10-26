import { create } from "zustand";
import {
  generateVideo,
  getBarometro,
  getChatEstado,
  getChatSugerencias,
  getEmpresas,
  getKpis,
  getVideoInfo,
  postChat,
} from "@/services/api";
import type {
  BarometroResumen,
  ChatEstado,
  ChatMessage,
  ChatSugerencia,
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
  chatEstado: ChatEstado | null;
  sugerencias: ChatSugerencia[];
  chatContexto: string | null;

  video: VideoResult | null;
  videoInfo: VideoInfo | null;
  videoLoading: boolean;
  videoError: string | null;

  loadHome: () => Promise<void>;
  loadEmpresas: (periodo?: string) => Promise<void>;
  sendChat: (text: string) => Promise<void>;
  enviarRapida: (sugerencia: ChatSugerencia) => void;
  setChatContexto: (contexto: string | null) => void;
  loadChatEstado: () => Promise<void>;
  resetChat: () => void;
  loadVideoInfo: () => Promise<void>;
  generateVideo: () => Promise<void>;
}

export const useAppStore = create<AppState>((set, get) => ({
  kpis: null,
  barometro: null,
  loading: false,
  error: null,

  empresas: [],
  empresasLoading: false,

  chat: [],
  chatLoading: false,
  chatEstado: null,
  sugerencias: [],
  chatContexto: null,

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
      const res = await postChat(text, get().chatContexto);
      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: res.answer,
        engine: res.engine,
        motivo: res.motivo,
        kind: "llm",
      };
      set((s) => ({ chat: [...s.chat, assistantMsg], chatLoading: false }));
    } catch (e) {
      const detalle = e instanceof Error ? e.message : "error";
      const esTimeout = detalle.toLowerCase().includes("timeout");
      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: esTimeout
          ? "El modelo tardó más de lo esperado y se agotó el tiempo de espera. " +
            "Vuelve a intentarlo; si se repite, revisa la conexión con el proveedor del modelo."
          : `No pude conectar con la API: ${detalle}`,
        kind: "llm",
      };
      set((s) => ({ chat: [...s.chat, assistantMsg], chatLoading: false }));
    }
  },

  // Las sugerencias ya traen su respuesta calculada: no consumen el modelo.
  enviarRapida: (sugerencia) =>
    set((s) => ({
      chat: [
        ...s.chat,
        { role: "user", content: sugerencia.pregunta },
        {
          role: "assistant",
          content: sugerencia.respuesta,
          kind: "rapida",
          motivo: "respuesta precalculada del dataset",
        },
      ],
    })),

  setChatContexto: (contexto) => set({ chatContexto: contexto }),

  loadChatEstado: async () => {
    try {
      const [chatEstado, sugerencias] = await Promise.all([
        getChatEstado(),
        getChatSugerencias(),
      ]);
      set({ chatEstado, sugerencias });
    } catch {
      set({ chatEstado: null });
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
