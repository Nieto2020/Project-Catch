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

export interface DimensionGlobal {
  clave: string;
  peso: number;
  meta: number;
  unidad: string;
  valor_actual: number;
  score: number;
}

export interface GlobalIndex {
  score: number;
  dimensiones: DimensionGlobal[];
}

export interface TopEmpresa {
  periodo: string;
  empresa: string;
  talla: string;
  score: number;
  salario_medio: number;
  rotacion_bimestral_pct: number;
  headcount: number;
}

export interface BarometroResumen {
  global: GlobalIndex;
  distribucion: { min: number; promedio: number; mediana: number; max: number };
  tendencia: { periodo: string; periodo_num: number; score_promedio: number }[];
  top5: TopEmpresa[];
  dimensiones: Record<string, number>;
}

export interface EmpresaScore {
  periodo: string;
  empresa: string;
  talla: string;
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

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  engine?: string;
}

export interface HallazgoVideo {
  titulo: string;
  narracion: string;
}

export interface VideoInfo {
  disponible: boolean;
  path: string | null;
  voz: string;
  hallazgos: HallazgoVideo[] | null;
}

export interface VideoResult {
  path: string;
  duracion_segundos: number | null;
  hallazgos: HallazgoVideo[];
}
