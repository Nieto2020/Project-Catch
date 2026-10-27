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
  valor_actual: number | null;
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
  /** Condiciones descriptivas: no ponderan el índice de competitividad. */
  dias_descanso_adicionales: number | null;
  vacaciones_dias: number | null;
  aguinaldo_dias: number | null;
  prima_vacacional_pct: number | null;
}

export interface VariableComparable {
  clave: string;
  etiqueta: string;
  grupo: string;
  unidad: string;
  tipo: "numerica" | "booleana";
  mejor: "alto" | "bajo";
  descripcion: string;
  resumen: string;
}

export interface ResumenComparable {
  n: number;
  cobertura_pct?: number | null;
  mediana?: number | null;
  promedio?: number | null;
  p25?: number | null;
  p75?: number | null;
  min?: number | null;
  max?: number | null;
  otorgan?: number;
  otorgan_pct?: number | null;
}

export interface EmpresaComparada {
  empresa: string;
  periodo: string;
  talla: string;
  score_competitividad: number | null;
  valor: number | null;
  otorga: boolean | null;
  mediana_talla: number | null;
  diferencia: number | null;
  diferencia_pct: number | null;
  percentil: number | null;
  pct_talla: number | null;
}

export interface ComparativaDescriptiva {
  variable: VariableComparable;
  periodo_efectivo: string;
  talla: string | null;
  resumen: ResumenComparable;
  por_talla: (ResumenComparable & { talla: string })[];
  por_periodo: (ResumenComparable & { periodo: string; periodo_num: number })[];
  empresas: EmpresaComparada[];
  variables: VariableComparable[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  engine?: string;
  motivo?: string;
  /** "rapida" = respuesta precalculada del dataset; "llm" = agente de lenguaje. */
  kind?: "rapida" | "llm";
}

export interface ChatSugerencia {
  pregunta: string;
  respuesta: string;
}

export interface ChatEstado {
  llm_disponible: boolean;
  modelo: string | null;
}
