import { useEffect, useMemo, useState } from "react";
import {
  Badge,
  Button,
  Callout,
  Card,
  Metric,
  ProgressBar,
  Text,
  Title,
} from "@tremor/react";
import { useAppStore } from "@/store/useAppStore";

const FIELDS: { key: string; label: string; step?: string }[] = [
  { key: "salario_inicial", label: "Salario inicial operativo (MXN/día)", step: "1" },
  { key: "salario_maximo", label: "Salario máximo operativo (MXN/día)", step: "1" },
  { key: "total_faltas", label: "Faltas bimestrales totales", step: "1" },
  { key: "hrs_cap_operativos", label: "Horas de capacitación (operativos)", step: "1" },
  { key: "pct_mujeres", label: "% de mujeres en plantilla (0-100)", step: "1" },
];

export default function WhatIf() {
  const { empresas, loadEmpresas, whatif, whatifLoading, whatifError, runWhatif } = useAppStore();
  const [empresa, setEmpresa] = useState<string>("");
  const [inputs, setInputs] = useState<Record<string, string>>({});

  useEffect(() => {
    loadEmpresas();
  }, [loadEmpresas]);

  const empresasUnicas = useMemo(() => {
    const seen = new Set<string>();
    return empresas.filter((e) => {
      if (seen.has(e.empresa)) return false;
      seen.add(e.empresa);
      return true;
    });
  }, [empresas]);

  const simulate = () => {
    const cambios: Record<string, number> = {};
    for (const f of FIELDS) {
      const raw = inputs[f.key];
      if (raw !== undefined && raw !== "") {
        const n = Number(raw);
        if (!Number.isNaN(n)) cambios[f.key] = n;
      }
    }
    runWhatif({
      empresa: empresa || null,
      cambios,
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Simulador What-If</h1>
        <p className="text-sm text-slate-500">
          Modifica variables y proyecta el impacto en la retención con el modelo de rotación.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <Title>Escenario</Title>
          <div className="mt-4 space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                Empresa base (opcional)
              </label>
              <select
                value={empresa}
                onChange={(e) => setEmpresa(e.target.value)}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
              >
                <option value="">Coorte promedio (mediana)</option>
                {empresasUnicas.map((e) => (
                  <option key={e.empresa} value={e.empresa}>
                    {e.empresa}
                  </option>
                ))}
              </select>
            </div>

            {FIELDS.map((f) => (
              <div key={f.key}>
                <label className="mb-1 block text-sm font-medium text-slate-700">{f.label}</label>
                <input
                  type="number"
                  step={f.step}
                  placeholder="Dejar vacío = sin cambio"
                  value={inputs[f.key] ?? ""}
                  onChange={(e) =>
                    setInputs((prev) => ({ ...prev, [f.key]: e.target.value }))
                  }
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                />
              </div>
            ))}

            <Button onClick={simulate} loading={whatifLoading} disabled={whatifLoading}>
              Simular impacto
            </Button>
          </div>
        </Card>

        <div className="space-y-4">
          {whatifError && (
            <Callout title="Error en la simulación" color="rose">
              {whatifError}
            </Callout>
          )}

          {!whatif && !whatifError && (
            <Card>
              <Text className="py-8 text-center">
                Ajusta las variables del escenario y pulsa “Simular impacto”.
              </Text>
            </Card>
          )}

          {whatif && (
            <>
              <Card decoration="top" decorationColor="cyan">
                <Title>Resultado proyectado</Title>
                <div className="mt-4 grid grid-cols-2 gap-4">
                  <div>
                    <Text>Rotación actual</Text>
                    <Metric>{whatif.rotacion_actual_pct.toFixed(2)}%</Metric>
                  </div>
                  <div>
                    <Text>Rotación proyectada</Text>
                    <Metric>{whatif.rotacion_proyectada_pct.toFixed(2)}%</Metric>
                  </div>
                </div>
                <div className="mt-4">
                  <Text>Cambio</Text>
                  <Badge size="lg" color={whatif.delta_pts_porcentuales < 0 ? "emerald" : "rose"}>
                    {whatif.delta_pts_porcentuales >= 0 ? "+" : ""}
                    {whatif.delta_pts_porcentuales.toFixed(2)} pts
                  </Badge>
                </div>
                <p className="mt-4 text-sm text-slate-600">{whatif.interpretacion}</p>
              </Card>

              <Card>
                <Title>Principales drivers del modelo</Title>
                <div className="mt-4 space-y-3">
                  {whatif.drivers_principales.slice(0, 5).map((d) => (
                    <div key={d.feature}>
                      <div className="flex justify-between text-sm">
                        <Text className="capitalize">{d.feature.replaceAll("_", " ")}</Text>
                        <Text>{(d.importance * 100).toFixed(1)}%</Text>
                      </div>
                      <ProgressBar value={d.importance * 100} className="mt-1" />
                    </div>
                  ))}
                </div>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
