import axios from "axios";
import type {
  BarometroResumen,
  DashboardData,
  EmpresaScore,
  WhatIfResult,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
});

export async function getDashboard(): Promise<DashboardData> {
  const { data } = await api.get<DashboardData>("/api/dashboard");
  return data;
}

export async function getBarometro(): Promise<BarometroResumen> {
  const { data } = await api.get<BarometroResumen>("/api/barometro");
  return data;
}

export async function getEmpresas(periodo?: string): Promise<EmpresaScore[]> {
  const { data } = await api.get<{ empresas: EmpresaScore[] }>("/api/empresas", {
    params: periodo ? { periodo } : {},
  });
  return data.empresas;
}

export async function getPeriodos(): Promise<string[]> {
  const { data } = await api.get<{ periodos: string[] }>("/api/periodos");
  return data.periodos;
}

export interface WhatIfPayload {
  empresa?: string | null;
  periodo?: string | null;
  cambios: Record<string, number>;
}

export async function postWhatif(payload: WhatIfPayload): Promise<WhatIfResult> {
  const { data } = await api.post<WhatIfResult>("/api/whatif", payload);
  return data;
}

export async function postChat(pregunta: string): Promise<{ answer: string; engine: string }> {
  const { data } = await api.post<{ answer: string; engine: string }>("/api/chat", {
    pregunta,
  });
  return data;
}
