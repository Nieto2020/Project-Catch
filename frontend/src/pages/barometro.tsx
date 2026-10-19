import { useEffect, useMemo, useState } from "react";
import {
  AreaChart,
  Badge,
  Card,
  Metric,
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

const scoreColor = (s: number) => (s >= 60 ? "emerald" : s >= 40 ? "amber" : "rose");

export default function Barometro() {
  const { barometro, empresas, loadEmpresas, loadDashboard, dashboardLoading } = useAppStore();
  const [periodo, setPeriodo] = useState<string>("");

  useEffect(() => {
    loadDashboard();
    loadEmpresas();
  }, [loadDashboard, loadEmpresas]);

  const periodos = useMemo(() => {
    const set = new Set(empresas.map((e) => e.periodo));
    return Array.from(set).sort();
  }, [empresas]);

  const filtradas = useMemo(
    () => (periodo ? empresas.filter((e) => e.periodo === periodo) : empresas),
    [empresas, periodo],
  );

  const top = useMemo(() => filtradas.slice(0, 10), [filtradas]);

  if (dashboardLoading && !barometro) {
    return <div className="py-20 text-center text-slate-500">Cargando barómetro…</div>;
  }

  const d = barometro?.distribucion;
  const tendencia = barometro?.tendencia ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Barómetro de Competitividad</h1>
        <p className="text-sm text-slate-500">
          Índice normalizado 0-100 por empresa: salario (30%), retención (30%), ausentismo (15%),
          capacitación (15%) y equilibrio de género (10%).
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card decoration="top" decorationColor="emerald">
          <Text>Máximo</Text>
          <Metric>{d?.max.toFixed(1)}</Metric>
        </Card>
        <Card decoration="top" decorationColor="cyan">
          <Text>Promedio</Text>
          <Metric>{d?.promedio.toFixed(1)}</Metric>
        </Card>
        <Card decoration="top" decorationColor="amber">
          <Text>Mediana</Text>
          <Metric>{d?.mediana.toFixed(1)}</Metric>
        </Card>
        <Card decoration="top" decorationColor="rose">
          <Text>Mínimo</Text>
          <Metric>{d?.min.toFixed(1)}</Metric>
        </Card>
      </div>

      <Card>
        <Title>Evolución del índice por bimestre</Title>
        <AreaChart
          className="mt-4 h-64"
          data={tendencia}
          index="periodo"
          categories={["score_promedio"]}
          colors={["cyan"]}
          showLegend={false}
          valueFormatter={(v: number) => v.toFixed(1)}
        />
      </Card>

      <Card>
        <div className="flex items-center justify-between">
          <Title>Ranking de empresas</Title>
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
        <Table className="mt-4">
          <TableHead>
            <TableRow>
              <TableHeaderCell>#</TableHeaderCell>
              <TableHeaderCell>Empresa</TableHeaderCell>
              <TableHeaderCell>Periodo</TableHeaderCell>
              <TableHeaderCell>Score</TableHeaderCell>
              <TableHeaderCell>Salario medio</TableHeaderCell>
              <TableHeaderCell>Rotación</TableHeaderCell>
              <TableHeaderCell>Headcount</TableHeaderCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {top.map((e, i) => (
              <TableRow key={`${e.periodo}-${e.empresa}`}>
                <TableCell>{i + 1}</TableCell>
                <TableCell className="font-medium">{e.empresa}</TableCell>
                <TableCell>{e.periodo}</TableCell>
                <TableCell>
                  <Badge color={scoreColor(e.score_competitividad)}>
                    {e.score_competitividad.toFixed(1)}
                  </Badge>
                </TableCell>
                <TableCell>${Math.round(e.salario_medio ?? 0).toLocaleString("es-MX")}</TableCell>
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
