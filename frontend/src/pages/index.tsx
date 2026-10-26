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
  ].join("\n");
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
    </div>
  );
}
