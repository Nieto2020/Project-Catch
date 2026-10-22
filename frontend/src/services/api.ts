import axios from "axios";
import type {
  BarometroResumen,
  EmpresaScore,
  Kpis,
  VideoInfo,
  VideoResult,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
});

export const videoApi = axios.create({
  baseURL: BASE_URL,
  timeout: 600000, // la generación del video puede tardar ~1 min
});

export function videoDownloadUrl(): string {
  return `${BASE_URL}/api/video/descargar`;
}

export async function getKpis(): Promise<Kpis> {
  const { data } = await api.get<Kpis>("/api/kpis");
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

export async function postChat(pregunta: string): Promise<{ answer: string; engine: string }> {
  const { data } = await api.post<{ answer: string; engine: string }>("/api/chat", {
    pregunta,
  });
  return data;
}

export async function getVideoInfo(): Promise<VideoInfo> {
  const { data } = await api.get<VideoInfo>("/api/video");
  return data;
}

export async function generateVideo(): Promise<VideoResult> {
  const { data } = await videoApi.post<VideoResult>("/api/video/generar");
  return data;
}

export interface ReportOpciones {
  empresas: string[];
  periodos: string[];
}

export async function getReportOpciones(): Promise<ReportOpciones> {
  const { data } = await api.get<ReportOpciones>("/api/report/opciones");
  return data;
}

export function reportUrl(empresa?: string, periodos?: string[]): string {
  const params = new URLSearchParams();
  if (empresa) params.set("empresa", empresa);
  if (periodos && periodos.length > 0) params.set("periodos", periodos.join(","));
  const qs = params.toString();
  return `${BASE_URL}/api/report${qs ? `?${qs}` : ""}`;
}

export function reportDownloadUrl(empresa?: string, periodos?: string[]): string {
  const params = new URLSearchParams();
  if (empresa) params.set("empresa", empresa);
  if (periodos && periodos.length > 0) params.set("periodos", periodos.join(","));
  const qs = params.toString();
  return `${BASE_URL}/api/report/descargar${qs ? `?${qs}` : ""}`;
}

export function reportPdfUrl(empresa?: string, periodos?: string[]): string {
  const params = new URLSearchParams();
  if (empresa) params.set("empresa", empresa);
  if (periodos && periodos.length > 0) params.set("periodos", periodos.join(","));
  const qs = params.toString();
  return `${BASE_URL}/api/report/pdf${qs ? `?${qs}` : ""}`;
}
