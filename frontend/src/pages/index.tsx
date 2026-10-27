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
import type { EmpresaScore } from "@/services/types";

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

/** Texto de contexto que se adjunta al chat al pulsar "Contexto con IA". */
function contextoDeFila(e: EmpresaScore): string {
  return [
    `Empresa: ${e.empresa}`,
    `Talla: ${e.talla}`,
    `Bimestre: ${e.periodo}`,
    `Score de competitividad: ${e.score_competitividad.toFixed(1)}/100`,
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

const TALLAS = ["Micro", "Pequeña", "Mediana", "Grande"];

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

/** Comparador de condiciones laborales que NO ponderan el índice. */
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
        <Title>Condiciones laborales comparadas</Title>
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
                  <TableHeaderCell className="whitespace-nowrap">Percentil</TableHeaderCell>
                  <TableHeaderCell className="whitespace-nowrap">Score</TableHeaderCell>
                </>
              ) : (
                <>
                  <TableHeaderCell className="whitespace-nowrap">¿Lo otorga?</TableHeaderCell>
                  <TableHeaderCell className="whitespace-nowrap">% de su talla</TableHeaderCell>
                  <TableHeaderCell className="whitespace-nowrap">Score</TableHeaderCell>
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
            forman parte del índice de competitividad.
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
  const router = useRouter();

  const abrirEnChat = (e: EmpresaScore) => {
    setChatContexto(contextoDeFila(e));
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

  const filtradas = useMemo(() => {
    let out = empresas;
    if (periodo) out = out.filter((e) => e.periodo === periodo);
    if (talla) out = out.filter((e) => e.talla === talla);
    if (!periodo) {
      // Una fila por empresa (la de mejor score) cuando se ven todos los periodos.
      const best = new Map<string, (typeof empresas)[number]>();
      for (const e of out) {
        const prev = best.get(e.empresa);
        if (!prev || e.score_competitividad > prev.score_competitividad) {
          best.set(e.empresa, e);
        }
      }
      out = Array.from(best.values());
    }
    return out;
  }, [empresas, periodo, talla]);

  if (loading && !barometro) {
    return <div className="py-20 text-center text-slate-500">Cargando barómetro…</div>;
  }

  if (error && !barometro) {
    return (
      <div className="mx-auto max-w-lg py-20 text-center">
        <p className="text-lg font-semibold text-red-600">No se pudo conectar con la API</p>
        <p className="mt-2 text-sm text-slate-500">
          Ejecuta <code className="rounded bg-slate-200 px-1">.\demo.ps1</code> o el backend en{" "}
          <code className="rounded bg-slate-200 px-1">127.0.0.1:8000</code>.
        </p>
      </div>
    );
  }

  if (!barometro || !kpis) return null;

  const gi = barometro.global;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Barómetro Global de Competitividad"
        subtitle="Índice 0-100 construido con métricas establecidas: salario (30%), retención (30%), ausentismo (15%), capacitación (15%) y equilibrio de género (10%)."
        icon="⚖️"
      />

      {/* Índice global + KPIs */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card decoration="top" decorationColor="blue">
          <Text>Índice global</Text>
          <Metric>{gi.score.toFixed(1)}</Metric>
          <Text className="mt-1">de 100</Text>
        </Card>
        <Card decoration="top" decorationColor="sky">
          <Text>Headcount total</Text>
          <Metric>{fmtInt(kpis.headcount_total)}</Metric>
          <Text className="mt-1">{kpis.empresas} empresas · {kpis.periodos} bimestres</Text>
        </Card>
        <Card decoration="top" decorationColor="indigo">
          <Text>Salario medio operativo</Text>
          <Metric>{fmtMoney(kpis.salario_medio_operativo)}</Metric>
          <Text className="mt-1">MXN/día</Text>
        </Card>
        <Card decoration="top" decorationColor="blue">
          <Text>Rotación bimestral</Text>
          <Metric>{fmtPct(kpis.rotacion_bimestral_promedio)}</Metric>
          <Text className="mt-1">faltas: {fmtInt(kpis.faltas_por_100_promedio)}/100</Text>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Desglose por dimensión */}
        <Card>
          <Title>Desglose del índice global</Title>
          <Text>Score 0-100 frente a la meta de cada dimensión</Text>
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
          <Title>Evolución del índice por bimestre</Title>
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

      {/* Ranking */}
      <Card>
        <div className="flex items-center justify-between gap-3">
          <Title>Ranking por talla de empresa</Title>
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
        <Table className="mt-4">
          <TableHead>
            <TableRow>
              <TableHeaderCell>#</TableHeaderCell>
              <TableHeaderCell>Empresa</TableHeaderCell>
              <TableHeaderCell>Talla</TableHeaderCell>
              <TableHeaderCell>Periodo</TableHeaderCell>
              <TableHeaderCell>Score</TableHeaderCell>
              <TableHeaderCell>Salario medio</TableHeaderCell>
              <TableHeaderCell>Rotación</TableHeaderCell>
              <TableHeaderCell>Headcount</TableHeaderCell>
              <TableHeaderCell>
                <span className="sr-only">Contexto con IA</span>
              </TableHeaderCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filtradas.slice(0, 10).map((e, i) => (
              <TableRow key={`${e.periodo}-${e.empresa}`}>
                <TableCell>{i + 1}</TableCell>
                <TableCell className="font-medium">{e.empresa}</TableCell>
                <TableCell>
                  <Badge color="blue" size="sm">
                    {e.talla}
                  </Badge>
                </TableCell>
                <TableCell>{e.periodo}</TableCell>
                <TableCell>
                  <Badge color={scoreColor(e.score_competitividad)}>
                    {e.score_competitividad.toFixed(1)}
                  </Badge>
                </TableCell>
                <TableCell>{fmtMoney(e.salario_medio ?? 0)}</TableCell>
                <TableCell>{e.rotacion_bimestral_pct?.toFixed(2)}%</TableCell>
                <TableCell>{e.headcount?.toLocaleString("es-MX")}</TableCell>
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
