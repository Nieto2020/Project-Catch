import { useEffect } from "react";
import {
  AreaChart,
  Badge,
  BarChart,
  Card,
  DonutChart,
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

const fmtMoney = (v: number) => `$${Math.round(v).toLocaleString("es-MX")}`;
const fmtPct = (v: number) => `${v.toFixed(2)}%`;
const fmtInt = (v: number) => Math.round(v).toLocaleString("es-MX");

export default function Dashboard() {
  const { dashboard, dashboardLoading, dashboardError, loadDashboard } = useAppStore();

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  if (dashboardLoading && !dashboard) {
    return <div className="py-20 text-center text-slate-500">Cargando dashboard…</div>;
  }

  if (dashboardError && !dashboard) {
    return (
      <div className="mx-auto max-w-lg py-20 text-center">
        <p className="text-lg font-semibold text-red-600">No se pudo conectar con la API</p>
        <p className="mt-2 text-slate-500">
          Asegúrate de tener el backend corriendo en{" "}
          <code className="rounded bg-slate-200 px-1">127.0.0.1:8000</code>:{" "}
          <code className="rounded bg-slate-200 px-1">
            .venv\Scripts\python.exe -m uvicorn backend.main:app --reload
          </code>
        </p>
        <p className="mt-2 text-sm text-slate-400">{dashboardError}</p>
      </div>
    );
  }

  if (!dashboard) return null;

  const { kpis, tendencias, distribuciones, barometro } = dashboard;
  const genderData = [
    { name: "Mujeres", value: kpis.mujeres_pct_promedio ?? 0 },
    { name: "Hombres", value: 100 - (kpis.mujeres_pct_promedio ?? 0) },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard Descriptivo</h1>
        <p className="text-sm text-slate-500">
          Indicadores de la encuesta bimestral de RH · {kpis.periodos} bimestres · {kpis.empresas}{" "}
          empresas
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card decoration="top" decorationColor="cyan">
          <Text>Headcount total</Text>
          <Metric>{fmtInt(kpis.headcount_total)}</Metric>
          <Text className="mt-1">mediana {fmtInt(kpis.headcount_promedio)} / empresa</Text>
        </Card>
        <Card decoration="top" decorationColor="blue">
          <Text>Salario medio operativo</Text>
          <Metric>{fmtMoney(kpis.salario_medio_operativo)}</Metric>
          <Text className="mt-1">MXN por día</Text>
        </Card>
        <Card decoration="top" decorationColor="amber">
          <Text>Rotación bimestral</Text>
          <Metric>{fmtPct(kpis.rotacion_bimestral_promedio)}</Metric>
          <Text className="mt-1">del headcount</Text>
        </Card>
        <Card decoration="top" decorationColor="rose">
          <Text>Faltas por 100 empleados</Text>
          <Metric>{fmtInt(kpis.faltas_por_100_promedio)}</Metric>
          <Text className="mt-1">por bimestre</Text>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <Title>Salario medio operativo por bimestre</Title>
          <Text>Mediana en MXN/día</Text>
          <AreaChart
            className="mt-4 h-72"
            data={tendencias}
            index="periodo"
            categories={["salario_medio_mediana"]}
            colors={["blue"]}
            valueFormatter={fmtMoney}
            showLegend={false}
          />
        </Card>
        <Card>
          <Title>Rotación y ausentismo</Title>
          <Text>Rotación bimestral % · faltas por 100</Text>
          <AreaChart
            className="mt-4 h-72"
            data={tendencias}
            index="periodo"
            categories={["rotacion_bimestral_media", "faltas_por_100_mediana"]}
            colors={["amber", "rose"]}
            valueFormatter={(v: number) => v.toFixed(1)}
          />
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card>
          <Title>Composición de género</Title>
          <Text>% mediano de la plantilla</Text>
          <DonutChart
            className="mt-4 h-56"
            data={genderData}
            category="value"
            index="name"
            colors={["violet", "cyan"]}
            valueFormatter={(v: number) => `${v.toFixed(0)}%`}
          />
        </Card>
        <Card>
          <Title>Distribución de headcount</Title>
          <Text>Empresas por tamaño</Text>
          <BarChart
            className="mt-4 h-56"
            data={distribuciones.headcount.buckets}
            index="rango"
            categories={["conteo"]}
            colors={["slate"]}
            showLegend={false}
            valueFormatter={fmtInt}
          />
        </Card>
        <Card>
          <Title>Generaciones (mediana %)</Title>
          <div className="mt-4 space-y-3">
            {Object.entries(distribuciones.generaciones).map(([k, v]) => (
              <div key={k} className="flex items-center justify-between">
                <Text className="capitalize">{k.replaceAll("_", " ")}</Text>
                <Badge size="sm">{v ?? "—"}%</Badge>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card>
        <Title>Top 5 — Barómetro de Competitividad</Title>
        <Table className="mt-4">
          <TableHead>
            <TableRow>
              <TableHeaderCell>Empresa</TableHeaderCell>
              <TableHeaderCell>Periodo</TableHeaderCell>
              <TableHeaderCell>Score</TableHeaderCell>
              <TableHeaderCell>Rotación</TableHeaderCell>
              <TableHeaderCell>Salario medio</TableHeaderCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {barometro.top5.map((t) => (
              <TableRow key={`${t.periodo}-${t.empresa}`}>
                <TableCell>{t.empresa}</TableCell>
                <TableCell>{t.periodo}</TableCell>
                <TableCell>
                  <Badge color={t.score >= 60 ? "emerald" : t.score >= 40 ? "amber" : "rose"}>
                    {t.score.toFixed(1)}
                  </Badge>
                </TableCell>
                <TableCell>{t.rotacion_bimestral_pct?.toFixed(2)}%</TableCell>
                <TableCell>{fmtMoney(t.salario_medio ?? 0)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}
