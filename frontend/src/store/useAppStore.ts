import { create } from "zustand";
import {
  getBarometro,
  getChatEstado,
  getChatSugerencias,
  getComparables,
  getEmpresas,
  getKpis,
  postChat,
} from "@/services/api";
import type {
  BarometroResumen,
  ChatEstado,
  ChatMessage,
  ChatSugerencia,
  ComparativaDescriptiva,
  EmpresaScore,
  Kpis,
} from "@/services/types";

interface AppState {
  kpis: Kpis | null;
  barometro: BarometroResumen | null;
  loading: boolean;
  error: string | null;

  empresas: EmpresaScore[];
  empresasLoading: boolean;

  comparables: ComparativaDescriptiva | null;
  comparablesLoading: boolean;

  chat: ChatMessage[];
  chatLoading: boolean;
  chatEstado: ChatEstado | null;
  sugerencias: ChatSugerencia[];
  chatContexto: string | null;

  loadHome: () => Promise<void>;
  loadEmpresas: (periodo?: string) => Promise<void>;
  loadComparables: (params?: { variable?: string; periodo?: string; talla?: string }) => Promise<void>;
  sendChat: (text: string) => Promise<void>;
  enviarRapida: (sugerencia: ChatSugerencia) => void;
  setChatContexto: (contexto: string | null) => void;
  loadChatEstado: () => Promise<void>;
  resetChat: () => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  kpis: null,
  barometro: null,
  loading: false,
  error: null,

  empresas: [],
  empresasLoading: false,

  comparables: null,
  comparablesLoading: false,

  chat: [],
  chatLoading: false,
  chatEstado: null,
  sugerencias: [],
  chatContexto: null,

  loadHome: async () => {
    set({ loading: true, error: null });
    // El backend puede estar arrancando (demo.ps1): se reintenta antes de rendirse.
    for (let intento = 0; intento < 3; intento++) {
      try {
        const [kpis, barometro] = await Promise.all([getKpis(), getBarometro()]);
        set({ kpis, barometro, loading: false });
        return;
      } catch (e) {
        if (intento < 2) {
          await new Promise((r) => setTimeout(r, 1200));
          continue;
        }
        set({
          error: e instanceof Error ? e.message : "Error al cargar el barómetro",
          loading: false,
        });
      }
    }
  },

  loadEmpresas: async (periodo) => {
    set({ empresasLoading: true });
    for (let intento = 0; intento < 3; intento++) {
      try {
        const empresas = await getEmpresas(periodo);
        set({ empresas, empresasLoading: false });
        return;
      } catch {
        if (intento < 2) await new Promise((r) => setTimeout(r, 1200));
      }
    }
    set({ empresasLoading: false });
  },

  // Variables descriptivas que no ponderan el índice (descansos, prestaciones).
  loadComparables: async (params) => {
    set({ comparablesLoading: true });
    try {
      const comparables = await getComparables(params);
      set({ comparables, comparablesLoading: false });
    } catch {
      set({ comparablesLoading: false });
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
      // Si el estado inicial no cargó (backend arrancando), se corrige solo.
      if (!get().chatEstado) void get().loadChatEstado();
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
    // El backend puede estar arrancando (demo.ps1, --reload): se reintenta.
    for (let intento = 0; intento < 3; intento++) {
      try {
        const [chatEstado, sugerencias] = await Promise.all([
          getChatEstado(),
          getChatSugerencias(),
        ]);
        set({ chatEstado, sugerencias });
        return;
      } catch {
        if (intento < 2) await new Promise((r) => setTimeout(r, 1200));
      }
    }
    set({ chatEstado: null });
  },

  resetChat: () => set({ chat: [] }),
}));
