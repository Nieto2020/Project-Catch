import { useEffect, useMemo, useState } from "react";
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

const fmtMoney = (v: number) => `$${Math.round(v).toLocaleString("es-MX")}`;
const fmtPct = (v: number) => `${v.toFixed(2)}%`;
const fmtInt = (v: number) => Math.round(v).toLocaleString("es-MX");

const scoreColor = (s: number) => (s >= 60 ? "emerald" : s >= 40 ? "amber" : "rose");

const DIM_LABELS: Record<string, string> = {
  salario: "Salario",
  retencion: "Retención",
  ausentismo: "Ausentismo",
  capacitacion: "Capacitación",
  equilibrio: "Equilibrio de género",
};

export default function BarometroGlobal() {
  const { kpis, barometro, loading, error, loadHome, empresas, loadEmpresas } = useAppStore();
  const [periodo, setPeriodo] = useState<string>("");
  const [talla, setTalla] = useState<string>("");

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
      <div>
        <h1 className="text-2xl font-bold">Barómetro Global de Competitividad</h1>
        <p className="text-sm text-slate-500">
          Índice 0-100 construido con métricas establecidas: salario (30%), retención (30%),
          ausentismo (15%), capacitación (15%) y equilibrio de género (10%).
        </p>
      </div>

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
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm"
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
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm"
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
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}
