import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/router";
import {
  AreaChart,
  Badge,
  Card,
  Metric,
  ProgressBar,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
  Text,
  Title,
} from "@tremor/react";
import { useAppStore } from "@/store/useAppStore";
import PageHeader from "@/components/PageHeader";
import Hint from "@/components/Hint";
import { postEscenario } from "@/services/api";
import type { DimensionGlobal, EmpresaScore, EscenarioIndice } from "@/services/types";

const fmtMoney = (v: number) => `$${Math.round(v).toLocaleString("es-MX")}`;
const fmtPct = (v: number) => `${v.toFixed(2)}%`;
const fmtInt = (v: number) => Math.round(v).toLocaleString("es-MX");
const fmtScore = (v: number | null | undefined) => (v == null ? "—" : v.toFixed(0));

// Escala monocromática azul para indicadores (solo azules y blancos).
const scoreColor = (s: number) => (s >= 60 ? "blue" : s >= 40 ? "sky" : "slate");

const DIM_LABELS: Record<string, string> = {
  salario: "Salario",
  retencion: "Retención",
  ausentismo: "Ausentismo",
  capacitacion: "Capacitación",
  equilibrio: "Equilibrio de género",
};

// Pesos por defecto del Índice SCORE (suman 100).
const PESOS_BASE: Record<string, number> = {
  salario: 30,
  retencion: 30,
  ausentismo: 15,
  capacitacion: 15,
  equilibrio: 10,
};

const ORDEN_DIMENSIONES = ["salario", "retencion", "ausentismo", "capacitacion", "equilibrio"];

const hayPesosPersonalizados = (pesos: Record<string, number>) =>
  ORDEN_DIMENSIONES.some((clave) => pesos[clave] !== PESOS_BASE[clave]);

/** "Salario 60% · Retención 20% · …" con los pesos ya normalizados. */
const resumenPesos = (pesos: Record<string, number>) => {
  const total = Object.values(pesos).reduce((a, b) => a + b, 0);
  return ORDEN_DIMENSIONES.filter((clave) => pesos[clave] > 0)
    .map(
      (clave) =>
        `${DIM_LABELS[clave]} ${total > 0 ? Math.round((pesos[clave] / total) * 100) : 0}%`,
    )
    .join(" · ");
};

/** Pide al backend el índice y los puntajes recalculados con otros pesos. */
function useEscenario(pesos: Record<string, number>) {
  const [resultado, setResultado] = useState<EscenarioIndice | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let vigente = true;
    // Pequeña espera para no disparar una petición por cada paso del control.
    const t = setTimeout(async () => {
      try {
        const data = await postEscenario(pesos);
        if (vigente) {
          setResultado(data);
          setError(false);
        }
      } catch {
        if (vigente) setError(true);
      }
    }, 250);
    return () => {
      vigente = false;
      clearTimeout(t);
    };
  }, [pesos]);

  return { resultado, error };
}

/** Comparador "qué pasa si…": mueve los pesos y recalcula índice y ranking. */
function EscenarioIndice({
  dimensiones,
  pesos,
  onPesos,
  resultado,
  error,
  personalizado,
}: {
  dimensiones: DimensionGlobal[];
  pesos: Record<string, number>;
  onPesos: (pesos: Record<string, number>) => void;
  resultado: EscenarioIndice | null;
  error: boolean;
  personalizado: boolean;
}) {
  const total = Object.values(pesos).reduce((a, b) => a + b, 0);
  const delta = resultado?.delta ?? 0;

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-1">
            <Title>Comparador “qué pasa si…”</Title>
            <Hint text="Recalcula el Índice SCORE y el ranking con otros pesos. Sirve para conversar con el cliente sobre qué priorizar, sin cambiar los datos." />
          </div>
          <Text className="mt-1">
            Ajusta cuánto pesa cada dimensión y observa el efecto en el índice y en el ranking.
          </Text>
        </div>
        <button
          type="button"
          onClick={() => onPesos(PESOS_BASE)}
          disabled={!personalizado}
          className="rounded-lg border border-brand-200 bg-white px-3 py-1.5 text-xs font-medium text-brand-700 shadow-sm transition hover:bg-brand-50 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Restablecer
        </button>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-3 lg:col-span-2">
          {ORDEN_DIMENSIONES.map((clave) => {
            const base = dimensiones.find((d) => d.clave === clave);
            const etiqueta = DIM_LABELS[clave] ?? clave;
            const normalizado = total > 0 ? Math.round((pesos[clave] / total) * 100) : 0;
            return (
              <div key={clave}>
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-slate-700">
                    {etiqueta}
                    <span className="ml-1 font-normal text-slate-400">
                      (mérito {base ? base.score.toFixed(0) : "—"}/100)
                    </span>
                  </span>
                  <span className="tabular-nums font-semibold text-brand-700">{normalizado}%</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={100}
                  step={5}
                  value={pesos[clave]}
                  onChange={(e) => onPesos({ ...pesos, [clave]: Number(e.target.value) })}
                  aria-label={`Peso de ${etiqueta}`}
                  className="mt-1 w-full cursor-pointer accent-brand-600"
                />
              </div>
            );
          })}
        </div>

        <div className="rounded-xl bg-brand-50/60 p-4 ring-1 ring-brand-100">
          <Text className="text-xs uppercase tracking-wide text-slate-500">Índice resultante</Text>
          <div className="mt-1 flex items-end gap-2">
            <span className="text-4xl font-bold tabular-nums text-brand-900">
              {resultado ? resultado.score.toFixed(1) : "—"}
            </span>
            {resultado && <Badge color={scoreColor(resultado.score)}>{resultado.banda}</Badge>}
          </div>
          <Text className="mt-1 text-xs text-slate-500">
            Base {resultado ? resultado.base.toFixed(1) : "—"} ·{" "}
            <span
              className={
                delta > 0 ? "font-semibold text-brand-700" : delta < 0 ? "font-semibold text-rose-600" : ""
              }
            >
              {delta > 0 ? "+" : ""}
              {delta.toFixed(1)} pts
            </span>
          </Text>
          {error && (
            <Text className="mt-2 text-xs text-rose-600">No se pudo recalcular el escenario.</Text>
          )}
          <Text className="mt-3 text-[11px] leading-relaxed text-slate-400">
            {personalizado
              ? "El ranking de abajo está calculado con estos pesos. Los puntajes por dimensión no cambian: solo su importancia."
              : "Los pesos se normalizan a 100%. Los puntajes por dimensión no cambian con el peso."}
          </Text>
        </div>
      </div>
    </Card>
  );
}

/** Texto de contexto que se adjunta al chat al pulsar "Contexto con IA". */
function contextoDeFila(
  e: EmpresaScore,
  score: number,
  delta: number | null,
  pesosPersonalizados: string | null = null,
): string {
  return [
    `Empresa: ${e.empresa}`,
    `Talla: ${e.talla}`,
    `Bimestre: ${e.periodo}`,
    `Índice SCORE: ${score.toFixed(1)}/100` +
      (delta != null
        ? ` (${delta > 0 ? "+" : ""}${delta.toFixed(1)} pts vs la mediana de su talla)`
        : "") +
      (pesosPersonalizados
        ? ` [recalculado con pesos personalizados: ${pesosPersonalizados}]`
        : ""),
    `Headcount: ${e.headcount?.toLocaleString("es-MX") ?? "—"}`,
    `Salario medio operativo: ${fmtMoney(e.salario_medio ?? 0)} MXN/día`,
    `Rotación bimestral: ${e.rotacion_bimestral_pct?.toFixed(2) ?? "—"}%`,
    `Sub-indicadores (0-100): salario ${fmtScore(e.sub_salario)}, ` +
      `retención ${fmtScore(e.sub_retencion)}, ausentismo ${fmtScore(e.sub_ausentismo)}, ` +
      `capacitación ${fmtScore(e.sub_capacitacion)}, equilibrio ${fmtScore(e.sub_equilibrio)}`,
    // Condiciones descriptivas: contexto para comparar, no forman parte del score.
    `Días de descanso adicionales a los festivos de ley: ${e.dias_descanso_adicionales ?? "—"}`,
    `Vacaciones (1.er año): ${e.vacaciones_dias ?? "—"} días · Aguinaldo: ${e.aguinaldo_dias ?? "—"} días · ` +
      `Prima vacacional: ${e.prima_vacacional_pct ?? "—"}%`,
  ].join("\n");
}

const fmtDeltaScore = (v: number | null | undefined) => {
  if (v == null) return "—";
  const signo = v > 0 ? "+" : "";
  return `${signo}${v.toFixed(1)} pts`;
};

const TALLAS = ["Micro", "Pequeña", "Mediana", "Grande"];

/** Esqueleto de carga: el pitch nunca debe mostrar una pantalla vacía. */
function CargandoBarometro() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Barómetro Global"
        subtitle="Índice SCORE 0-100 · cargando indicadores del dataset…"
        icon="⚖️"
      />
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Card key={i}>
            <div className="h-3 w-24 animate-pulse rounded bg-slate-200" />
            <div className="mt-3 h-7 w-20 animate-pulse rounded bg-slate-200" />
            <div className="mt-3 h-3 w-28 animate-pulse rounded bg-slate-100" />
          </Card>
        ))}
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {[0, 1].map((i) => (
          <Card key={i}>
            <div className="h-4 w-40 animate-pulse rounded bg-slate-200" />
            <div className="mt-4 h-52 animate-pulse rounded-xl bg-slate-100" />
          </Card>
        ))}
      </div>
      <Card>
        <div className="h-4 w-48 animate-pulse rounded bg-slate-200" />
        <div className="mt-4 space-y-2">
          {[0, 1, 2, 3, 4].map((i) => (
            <div key={i} className="h-8 animate-pulse rounded bg-slate-100" />
          ))}
        </div>
      </Card>
    </div>
  );
}

const fmtVariable = (v: number | null, unidad: string) => {
  if (v == null) return "—";
  const txt = v % 1 === 0 ? v.toFixed(0) : v.toFixed(1);
  if (unidad === "%") return `${txt}%`;
  if (!unidad) return txt;
  return `${txt} ${unidad === "días" && Math.abs(v) === 1 ? "día" : unidad}`;
};

const fmtDelta = (v: number | null, unidad: string) => {
  if (v == null) return "—";
  const signo = v > 0 ? "+" : "";
  const txt = v % 1 === 0 ? v.toFixed(0) : v.toFixed(1);
  if (unidad === "%") return `${signo}${txt} pp`;
  if (!unidad) return `${signo}${txt}`;
  return `${signo}${txt} ${unidad === "días" && Math.abs(v) === 1 ? "día" : unidad}`;
};

/** Comparador de condiciones laborales que NO ponderan el Índice SCORE. */
function ComparadorCondiciones() {
  const { comparables, comparablesLoading, loadComparables } = useAppStore();
  const [variable, setVariable] = useState("");
  const [periodo, setPeriodo] = useState("");
  const [talla, setTalla] = useState("");

  useEffect(() => {
    loadComparables({
      variable: variable || undefined,
      periodo: periodo || undefined,
      talla: talla || undefined,
    });
  }, [variable, periodo, talla, loadComparables]);

  if (!comparables) {
    return (
      <Card>
        <div className="flex items-center gap-1">
          <Title>Condiciones laborales comparadas</Title>
          <Hint text="Prestaciones y descansos que describen el empleo pero no suman puntos al Índice SCORE." />
        </div>
        <Text className="mt-2">
          {comparablesLoading ? "Cargando comparador…" : "Sin datos descriptivos disponibles."}
        </Text>
      </Card>
    );
  }

  const v = comparables.variable;
  const esNumerica = v.tipo === "numerica";
  const empresas = comparables.empresas;
  const periodos = comparables.por_periodo.map((p) => p.periodo);
  const grupos = Array.from(new Set(comparables.variables.map((x) => x.grupo)));
  const serie = comparables.por_periodo.map((p) => ({
    periodo: p.periodo,
    valor: (esNumerica ? p.mediana : p.otorgan_pct) ?? 0,
  }));

  const selectClass =
    "rounded-lg border border-brand-200 bg-white px-3 py-1.5 text-sm text-slate-700 shadow-sm outline-none transition focus:border-brand-400 focus:ring-2 focus:ring-brand-100";

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <Title>Condiciones laborales comparadas</Title>
            <Badge color="slate" size="sm">
              No pondera en el índice
            </Badge>
            <Hint text="Estas condiciones describen el empleo y permiten comparar empresas, pero no suman puntos al Índice SCORE." />
          </div>
          <Text className="mt-1 max-w-2xl">{v.descripcion}</Text>
        </div>
        <div className="flex flex-wrap gap-2">
          <select
            value={variable || v.clave}
            onChange={(e) => setVariable(e.target.value)}
            className={selectClass}
            aria-label="Variable a comparar"
          >
            {grupos.map((g) => (
              <optgroup key={g} label={g}>
                {comparables.variables
                  .filter((x) => x.grupo === g)
                  .map((x) => (
                    <option key={x.clave} value={x.clave}>
                      {x.etiqueta} · {x.resumen}
                    </option>
                  ))}
              </optgroup>
            ))}
          </select>
          <select
            value={periodo}
            onChange={(e) => setPeriodo(e.target.value)}
            className={selectClass}
            aria-label="Bimestre"
          >
            <option value="">Último bimestre ({comparables.periodo_efectivo})</option>
            {periodos.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
          <select
            value={talla}
            onChange={(e) => setTalla(e.target.value)}
            className={selectClass}
            aria-label="Talla"
          >
            <option value="">Todas las tallas</option>
            {TALLAS.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <div className="rounded-xl bg-brand-50/60 px-4 py-3 ring-1 ring-brand-100">
          <Text className="text-xs uppercase tracking-wide text-slate-500">
            {esNumerica ? "Mediana de la cohorte" : "Empresas que lo otorgan"}
            <Hint text="Valor central de todas las empresas seleccionadas. La mitad está por debajo; no es un promedio." />
          </Text>
          <p className="mt-1 text-xl font-semibold text-brand-800">
            {esNumerica
              ? fmtVariable(comparables.resumen.mediana ?? null, v.unidad)
              : `${comparables.resumen.otorgan_pct ?? 0}%`}
          </p>
        </div>
        <div className="rounded-xl bg-brand-50/60 px-4 py-3 ring-1 ring-brand-100">
          <Text className="text-xs uppercase tracking-wide text-slate-500">
            {esNumerica ? "Rango P25–P75" : "Registros que lo otorgan"}
          </Text>
          <p className="mt-1 text-xl font-semibold text-brand-800">
            {esNumerica
              ? `${fmtVariable(comparables.resumen.p25 ?? null, v.unidad)} – ${fmtVariable(
                  comparables.resumen.p75 ?? null,
                  v.unidad,
                )}`
              : `${comparables.resumen.otorgan ?? 0} de ${comparables.resumen.n}`}
          </p>
        </div>
        <div className="rounded-xl bg-brand-50/60 px-4 py-3 ring-1 ring-brand-100">
          <Text className="text-xs uppercase tracking-wide text-slate-500">
            {esNumerica ? "Mínimo – máximo" : "Cobertura"}
          </Text>
          <p className="mt-1 text-xl font-semibold text-brand-800">
            {esNumerica
              ? `${fmtVariable(comparables.resumen.min ?? null, v.unidad)} – ${fmtVariable(
                  comparables.resumen.max ?? null,
                  v.unidad,
                )}`
              : `${comparables.resumen.n} empresas`}
          </p>
        </div>
        <div className="rounded-xl bg-brand-50/60 px-4 py-3 ring-1 ring-brand-100">
          <Text className="text-xs uppercase tracking-wide text-slate-500">
            Empresas comparadas
          </Text>
          <p className="mt-1 text-xl font-semibold text-brand-800">
            {empresas.length}
            <span className="ml-1 text-sm font-normal text-slate-500">
              · {comparables.periodo_efectivo}
            </span>
          </p>
        </div>
      </div>

      <div className="mt-5 max-h-96 overflow-auto rounded-lg ring-1 ring-slate-100">
        <Table className="text-xs">
          <TableHead className="sticky top-0 bg-white">
            <TableRow>
              <TableHeaderCell className="whitespace-nowrap">#</TableHeaderCell>
              <TableHeaderCell className="whitespace-nowrap">Empresa</TableHeaderCell>
              <TableHeaderCell className="whitespace-nowrap">Talla</TableHeaderCell>
              {esNumerica ? (
                <>
                  <TableHeaderCell className="whitespace-nowrap">Valor</TableHeaderCell>
                  <TableHeaderCell className="whitespace-nowrap">Mediana talla</TableHeaderCell>
                  <TableHeaderCell className="whitespace-nowrap">vs talla</TableHeaderCell>
                  <TableHeaderCell className="whitespace-nowrap">
                    Percentil
                    <span
                      title="Posición de la empresa dentro de su talla: 99 = la que más otorga, 1 = la que menos."
                      aria-label="Posición de la empresa dentro de su talla: 99 = la que más otorga, 1 = la que menos."
                      className="ml-1 inline-flex h-4 w-4 cursor-help items-center justify-center rounded-full border border-slate-300 bg-white text-[10px] font-bold leading-none text-slate-500"
                    >
                      ?
                    </span>
                  </TableHeaderCell>
                  <TableHeaderCell className="whitespace-nowrap">Índice SCORE</TableHeaderCell>
                </>
              ) : (
                <>
                  <TableHeaderCell className="whitespace-nowrap">¿Lo otorga?</TableHeaderCell>
                  <TableHeaderCell className="whitespace-nowrap">% de su talla</TableHeaderCell>
                  <TableHeaderCell className="whitespace-nowrap">Índice SCORE</TableHeaderCell>
                </>
              )}
            </TableRow>
          </TableHead>
          <TableBody>
            {empresas.map((e, i) => (
              <TableRow key={`${e.empresa}-${e.periodo}`}>
                <TableCell>{i + 1}</TableCell>
                <TableCell className="font-medium">{e.empresa}</TableCell>
                <TableCell>
                  <Badge color="blue" size="sm">
                    {e.talla}
                  </Badge>
                </TableCell>
                {esNumerica ? (
                  <>
                    <TableCell>{fmtVariable(e.valor, v.unidad)}</TableCell>
                    <TableCell>{fmtVariable(e.mediana_talla, v.unidad)}</TableCell>
                    <TableCell
                      className={
                        (e.diferencia ?? 0) > 0
                          ? "text-brand-700"
                          : (e.diferencia ?? 0) < 0
                            ? "text-rose-600"
                            : "text-slate-500"
                      }
                    >
                      {fmtDelta(e.diferencia, v.unidad)}
                    </TableCell>
                    <TableCell>{e.percentil == null ? "—" : e.percentil.toFixed(0)}</TableCell>
                    <TableCell>
                      {e.score_competitividad == null ? "—" : e.score_competitividad.toFixed(1)}
                    </TableCell>
                  </>
                ) : (
                  <>
                    <TableCell>
                      <Badge color={e.otorga ? "blue" : "slate"} size="sm">
                        {e.otorga ? "Sí" : "No"}
                      </Badge>
                    </TableCell>
                    <TableCell>{e.pct_talla == null ? "—" : `${e.pct_talla}%`}</TableCell>
                    <TableCell>
                      {e.score_competitividad == null ? "—" : e.score_competitividad.toFixed(1)}
                    </TableCell>
                  </>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Text className="text-xs uppercase tracking-wide text-slate-500">
            {esNumerica ? "Mediana por bimestre" : "% de empresas por bimestre"}
          </Text>
          <AreaChart
            className="mt-2 h-48"
            data={serie}
            index="periodo"
            categories={["valor"]}
            colors={["blue"]}
            showLegend={false}
            valueFormatter={(n: number) => fmtVariable(n, v.unidad)}
          />
        </div>

        <div>
          <Text className="text-xs uppercase tracking-wide text-slate-500">
            {esNumerica ? "Mediana por talla" : "% por talla"}
          </Text>
          <div className="mt-2 flex flex-wrap gap-2">
            {comparables.por_talla.map((t) => (
              <span
                key={t.talla}
                className="rounded-full border border-brand-200 bg-white px-2.5 py-1 text-xs text-slate-600"
              >
                <span className="font-semibold text-brand-800">{t.talla}</span>{" "}
                {esNumerica
                  ? fmtVariable(t.mediana ?? null, v.unidad)
                  : `${t.otorgan_pct ?? 0}%`}
              </span>
            ))}
          </div>
          <Text className="mt-4 text-xs leading-relaxed text-slate-400">
            Estas variables describen condiciones de trabajo y sirven para comparar empresas; no
            forman parte del Índice SCORE.
          </Text>
        </div>
      </div>
    </Card>
  );
}

export default function BarometroGlobal() {
  const { kpis, barometro, loading, error, loadHome, empresas, loadEmpresas, setChatContexto } =
    useAppStore();
  const [periodo, setPeriodo] = useState<string>("");
  const [talla, setTalla] = useState<string>("");
  const [pesos, setPesos] = useState<Record<string, number>>(PESOS_BASE);
  const { resultado: escenario, error: errorEscenario } = useEscenario(pesos);
  const personalizado = hayPesosPersonalizados(pesos);
  const router = useRouter();

  // Puntajes del escenario indexados por empresa+bimestre.
  const scoresEscenario = useMemo(() => {
    if (!personalizado || !escenario) return null;
    const mapa = new Map<string, { score: number; delta: number | null }>();
    for (const e of escenario.empresas) {
      mapa.set(`${e.empresa}|${e.periodo}`, {
        score: e.score_competitividad,
        delta: e.delta_talla,
      });
    }
    return mapa;
  }, [personalizado, escenario]);

  const scoreDe = (e: EmpresaScore) =>
    scoresEscenario?.get(`${e.empresa}|${e.periodo}`) ?? {
      score: e.score_competitividad,
      delta: e.delta_talla,
    };

  const abrirEnChat = (e: EmpresaScore) => {
    const { score, delta } = scoreDe(e);
    setChatContexto(
      contextoDeFila(e, score, delta, personalizado ? resumenPesos(pesos) : null),
    );
    router.push("/chat");
  };

  useEffect(() => {
    loadHome();
    loadEmpresas();
  }, [loadHome, loadEmpresas]);

  const periodos = useMemo(() => {
    const set = new Set(empresas.map((e) => e.periodo));
    return Array.from(set).sort();
  }, [empresas]);

  const tallas = useMemo(() => {
    const orden = ["Micro", "Pequeña", "Mediana", "Grande"];
    const set = new Set(empresas.map((e) => e.talla));
    return Array.from(set).sort((a, b) => orden.indexOf(a) - orden.indexOf(b));
  }, [empresas]);

  // Ranking con los puntajes vigentes (base o escenario).
  const filtradas = useMemo(() => {
    let out = empresas;
    if (periodo) out = out.filter((e) => e.periodo === periodo);
    if (talla) out = out.filter((e) => e.talla === talla);
    const puntaje = (e: EmpresaScore) =>
      scoresEscenario?.get(`${e.empresa}|${e.periodo}`)?.score ?? e.score_competitividad;
    if (!periodo) {
      // Una fila por empresa (la de mejor puntaje) cuando se ven todos los periodos.
      const best = new Map<string, EmpresaScore>();
      for (const e of out) {
        const prev = best.get(e.empresa);
        if (!prev || puntaje(e) > puntaje(prev)) best.set(e.empresa, e);
      }
      out = Array.from(best.values());
    }
    // Agrupa por talla para que el ranking se lea de un vistazo.
    return [...out]
      .map((e) => {
        const alt = scoresEscenario?.get(`${e.empresa}|${e.periodo}`);
        return { fila: e, score: alt?.score ?? e.score_competitividad, delta: alt?.delta ?? e.delta_talla };
      })
      .sort(
        (a, b) => TALLAS.indexOf(a.fila.talla) - TALLAS.indexOf(b.fila.talla) || b.score - a.score,
      );
  }, [empresas, periodo, talla, scoresEscenario]);

  // Posición dentro de cada talla: el ranking compara pares del mismo tamaño.
  const posiciones = useMemo(() => {
    const contador = new Map<string, number>();
    return filtradas.map(({ fila }) => {
      const n = (contador.get(fila.talla) ?? 0) + 1;
      contador.set(fila.talla, n);
      return n;
    });
  }, [filtradas]);

  if (loading && !barometro) {
    return <CargandoBarometro />;
  }

  if (error && !barometro) {
    return (
      <div className="mx-auto max-w-lg py-20 text-center">
        <p className="text-lg font-semibold text-red-600">No se pudo conectar con la API</p>
        <p className="mt-2 text-sm text-slate-500">
          Ejecuta <code className="rounded bg-slate-200 px-1">.\demo.ps1</code> o el backend en{" "}
          <code className="rounded bg-slate-200 px-1">127.0.0.1:8000</code>.
        </p>
        <button
          type="button"
          onClick={() => loadHome()}
          className="mt-4 rounded-xl border border-brand-200 bg-white px-4 py-2 text-sm font-medium text-brand-700 shadow-sm transition hover:bg-brand-50"
        >
          Reintentar
        </button>
      </div>
    );
  }

  if (!barometro || !kpis) return null;

  const gi = barometro.global;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Barómetro Global"
        subtitle="Índice SCORE 0-100 construido con métricas establecidas: salario (30%), retención (30%), ausentismo (15%), capacitación (15%) y equilibrio de género (10%)."
        icon="⚖️"
      />

      {/* Índice global + KPIs */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card decoration="top" decorationColor="blue">
          <div className="flex items-center gap-1">
            <Text>Índice SCORE</Text>
            <Hint text="Promedio ponderado de 5 dimensiones (0-100). Arriba de 60 se considera Alto y de 80, Destacado." />
          </div>
          <div className="flex items-end gap-2">
            <Metric>{(personalizado && escenario ? escenario.score : gi.score).toFixed(1)}</Metric>
            <Badge
              color={scoreColor(personalizado && escenario ? escenario.score : gi.score)}
              className="mb-1"
            >
              {personalizado && escenario ? escenario.banda : barometro.lectura.banda}
            </Badge>
          </div>
          <Text className="mt-1">
            de 100
            {personalizado ? ` · escenario (base ${gi.score.toFixed(1)})` : ""}
          </Text>
        </Card>
        <Card decoration="top" decorationColor="sky">
          <div className="flex items-center gap-1">
            <Text>Headcount total</Text>
            <Hint text="Empleados sumados de todas las empresas y bimestres incluidos en el análisis." />
          </div>
          <Metric>{fmtInt(kpis.headcount_total)}</Metric>
          <Text className="mt-1">{kpis.empresas} empresas · {kpis.periodos} bimestres</Text>
        </Card>
        <Card decoration="top" decorationColor="indigo">
          <div className="flex items-center gap-1">
            <Text>Salario medio operativo</Text>
            <Hint text="Mediana del salario diario del personal operativo. La mitad de los registros está por debajo de esta cifra." />
          </div>
          <Metric>{fmtMoney(kpis.salario_medio_operativo)}</Metric>
          <Text className="mt-1">MXN/día</Text>
        </Card>
        <Card decoration="top" decorationColor="blue">
          <div className="flex items-center gap-1">
            <Text>Rotación bimestral</Text>
            <Hint text="Bajas del bimestre respecto al headcount. Las faltas por cada 100 empleados miden ausentismo." />
          </div>
          <Metric>{fmtPct(kpis.rotacion_bimestral_promedio)}</Metric>
          <Text className="mt-1">faltas: {fmtInt(kpis.faltas_por_100_promedio)}/100</Text>
        </Card>
      </div>

      {/* Lectura del índice: el número explicado en una línea */}
      <Card className="border-l-4 border-l-brand-600">
        <div className="space-y-1">
          <Text className="text-base font-semibold text-brand-900">
            {barometro.lectura.titulo}
          </Text>
          <Text>{barometro.lectura.comparacion}</Text>
          <Text className="text-slate-600">{barometro.lectura.palanca}</Text>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Desglose por dimensión */}
        <Card>
          <div className="flex items-center gap-1">
            <Title>Desglose del Índice SCORE</Title>
            <Hint text="Cada dimensión se puntúa de 0 a 100 comparando la métrica de la cohorte contra su meta: salario 500 MXN/día, rotación ≤15%, faltas ≤150, capacitación ≥4 h y 50% mujeres." />
          </div>
          <Text>Puntaje 0-100 frente a la meta de cada dimensión</Text>
          <div className="mt-4 space-y-4">
            {gi.dimensiones.map((d) => (
              <div key={d.clave}>
                <div className="flex items-center justify-between text-sm">
                  <Text className="font-medium">{DIM_LABELS[d.clave] ?? d.clave}</Text>
                  <Text>
                    {d.score.toFixed(0)}/100 · peso {Math.round(d.peso * 100)}%
                  </Text>
                </div>
                <ProgressBar value={d.score} color={scoreColor(d.score)} className="mt-1" />
                <Text className="mt-1 text-xs text-slate-500">
                  {d.valor_actual == null
                    ? "Sin dato del periodo"
                    : `Actual ${d.valor_actual.toLocaleString("es-MX", {
                        maximumFractionDigits: 2,
                      })} ${d.unidad}`}{" "}
                  · meta {d.meta.toLocaleString("es-MX")} {d.unidad}
                </Text>
              </div>
            ))}
          </div>
        </Card>

        {/* Tendencia */}
        <Card>
          <div className="flex items-center gap-1">
            <Title>Evolución del Índice SCORE por bimestre</Title>
            <Hint text="Promedio del índice de todas las empresas en cada bimestre. Muestra si la cohorte mejora o empeora con el tiempo." />
          </div>
          <AreaChart
            className="mt-4 h-64"
            data={barometro.tendencia}
            index="periodo"
            categories={["score_promedio"]}
            colors={["blue"]}
            showLegend={false}
            valueFormatter={(v: number) => v.toFixed(1)}
          />
        </Card>
      </div>

      <EscenarioIndice
        dimensiones={gi.dimensiones}
        pesos={pesos}
        onPesos={setPesos}
        resultado={escenario}
        error={errorEscenario}
        personalizado={personalizado}
      />

      {/* Ranking */}
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-1">
              <Title>Ranking por talla de empresa</Title>
              <Hint text="Cada empresa se compara con la mediana de su propia talla en el mismo bimestre. Si mueves los pesos del comparador, este ranking se recalcula." />
            </div>
            <Text className="mt-1">
              Cada empresa se compara con la mediana de su propia talla en el mismo bimestre.
            </Text>
          </div>
          <div className="flex gap-2">
            <select
              value={talla}
              onChange={(e) => setTalla(e.target.value)}
              className="rounded-lg border border-brand-200 bg-white px-3 py-1.5 text-sm text-slate-700 shadow-sm outline-none transition focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
            >
              <option value="">Todas las tallas</option>
              {tallas.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <select
              value={periodo}
              onChange={(e) => {
                const p = e.target.value;
                setPeriodo(p);
                loadEmpresas(p || undefined);
              }}
              className="rounded-lg border border-brand-200 bg-white px-3 py-1.5 text-sm text-slate-700 shadow-sm outline-none transition focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
            >
              <option value="">Todos los periodos</option>
              {periodos.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>
        </div>

        {personalizado && (
          <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900 ring-1 ring-amber-200">
            <span className="font-semibold">Ranking con pesos personalizados</span>
            <span>{resumenPesos(pesos)}</span>
            <button
              type="button"
              onClick={() => setPesos(PESOS_BASE)}
              className="ml-auto font-semibold underline decoration-amber-400 underline-offset-2 hover:text-amber-950"
            >
              Volver a los pesos base
            </button>
          </div>
        )}

        <Table className="mt-4">
          <TableHead>
            <TableRow>
              <TableHeaderCell># talla</TableHeaderCell>
              <TableHeaderCell>Empresa</TableHeaderCell>
              <TableHeaderCell>Talla</TableHeaderCell>
              <TableHeaderCell>Índice SCORE</TableHeaderCell>
              <TableHeaderCell>
                vs. su talla
                <Hint text="Diferencia en puntos contra la mediana de las empresas del mismo tamaño, en el mismo bimestre." />
              </TableHeaderCell>
              <TableHeaderCell>Salario medio</TableHeaderCell>
              <TableHeaderCell>Rotación</TableHeaderCell>
              <TableHeaderCell>
                <span className="sr-only">Contexto con IA</span>
              </TableHeaderCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filtradas.slice(0, 10).map(({ fila: e, score, delta }, i) => (
              <TableRow key={`${e.periodo}-${e.empresa}`}>
                <TableCell>{posiciones[i]}</TableCell>
                <TableCell>
                  <span className="font-medium">{e.empresa}</span>
                  <span className="mt-0.5 block text-[11px] text-slate-400">
                    {e.periodo} · {e.headcount?.toLocaleString("es-MX")} empleados
                  </span>
                </TableCell>
                <TableCell>
                  <Badge color="blue" size="sm">
                    {e.talla}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge color={scoreColor(score)}>{score.toFixed(1)}</Badge>
                </TableCell>
                <TableCell
                  className={
                    (delta ?? 0) > 0
                      ? "font-medium text-brand-700"
                      : (delta ?? 0) < 0
                        ? "font-medium text-rose-600"
                        : "text-slate-500"
                  }
                >
                  {fmtDeltaScore(delta)}
                </TableCell>
                <TableCell>{fmtMoney(e.salario_medio ?? 0)}</TableCell>
                <TableCell>{e.rotacion_bimestral_pct?.toFixed(2)}%</TableCell>
                <TableCell className="text-right">
                  <button
                    type="button"
                    onClick={() => abrirEnChat(e)}
                    title={`Preguntar a la IA sobre ${e.empresa} (${e.periodo})`}
                    aria-label={`Preguntar a la IA sobre ${e.empresa} en ${e.periodo}`}
                    className="group inline-flex items-center gap-1.5 rounded-full border border-brand-200 bg-white px-2.5 py-1 text-[11px] font-semibold text-brand-700 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-brand-500 hover:bg-brand-600 hover:text-white hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-300 active:translate-y-0"
                  >
                    <span
                      aria-hidden
                      className="text-[13px] leading-none transition-transform duration-200 group-hover:rotate-12 group-hover:scale-110"
                    >
                      ✨
                    </span>
                    Contexto con IA
                  </button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      <ComparadorCondiciones />
    </div>
  );
}
