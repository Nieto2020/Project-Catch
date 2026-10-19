export interface Kpis {
  empresas: number;
  periodos: number;
  registros: number;
  headcount_total: number;
  headcount_promedio: number;
  salario_medio_operativo: number;
  salario_inicial_promedio: number;
  salario_maximo_promedio: number;
  rotacion_bimestral_promedio: number;
  faltas_por_100_promedio: number;
  capacitacion_hrs_promedio: number;
  mujeres_pct_promedio: number;
}

export interface Tendencia {
  periodo: string;
  periodo_num: number;
  empresas: number;
  headcount_mediana: number;
  salario_medio_mediana: number;
  rotacion_bimestral_media: number;
  faltas_por_100_mediana: number;
}

export interface Bucket {
  rango: string;
  conteo: number;
}

export interface Distribuciones {
  headcount: { buckets: Bucket[]; min: number; mediana: number; max: number };
  salario_medio: { histograma: Bucket[]; min: number; mediana: number; max: number };
  rotacion_bimestral: { histograma: Bucket[]; mediana: number; max: number };
  generaciones: Record<string, number>;
}

export interface TopEmpresa {
  periodo: string;
  empresa: string;
  score: number;
  salario_medio: number;
  rotacion_bimestral_pct: number;
  headcount: number;
}

export interface BarometroResumen {
  distribucion: { min: number; promedio: number; mediana: number; max: number };
  tendencia: { periodo: string; periodo_num: number; score_promedio: number }[];
  top5: TopEmpresa[];
  dimensiones: Record<string, number>;
}

export interface DashboardData {
  kpis: Kpis;
  tendencias: Tendencia[];
  distribuciones: Distribuciones;
  barometro: BarometroResumen;
}

export interface EmpresaScore {
  periodo: string;
  empresa: string;
  score_competitividad: number;
  sub_salario: number;
  sub_retencion: number;
  sub_ausentismo: number;
  sub_capacitacion: number;
  sub_equilibrio: number;
  salario_medio: number;
  rotacion_bimestral_pct: number;
  headcount: number;
}

export interface Driver {
  feature: string;
  importance: number;
}

export interface WhatIfResult {
  escenario: string;
  empresa: string | null;
  periodo: string | null;
  rotacion_actual_pct: number;
  rotacion_proyectada_pct: number;
  delta_pts_porcentuales: number;
  cambios_aplicados: Record<string, number>;
  drivers_principales: Driver[];
  interpretacion: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  engine?: string;
}
