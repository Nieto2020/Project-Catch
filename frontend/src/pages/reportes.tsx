import { useEffect, useMemo, useState } from "react";
import { Button, Card, Text, Title } from "@tremor/react";
import {
  getReportOpciones,
  reportDownloadUrl,
  reportPdfUrl,
  reportUrl,
  type ReportOpciones,
} from "@/services/api";
import PageHeader from "@/components/PageHeader";

export default function Reportes() {
  const [opciones, setOpciones] = useState<ReportOpciones | null>(null);
  const [empresa, setEmpresa] = useState<string>("");
  const [periodos, setPeriodos] = useState<string[]>([]);
  const [url, setUrl] = useState<string>("");

  useEffect(() => {
    getReportOpciones()
      .then(setOpciones)
      .catch(() => setOpciones(null));
  }, []);

  const todosSeleccionados = useMemo(
    () => opciones != null && periodos.length === opciones.periodos.length,
    [periodos, opciones],
  );

  const togglePeriodo = (p: string) => {
    setPeriodos((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p],
    );
  };

  const toggleTodos = () => {
    if (!opciones) return;
    setPeriodos(todosSeleccionados ? [] : [...opciones.periodos]);
  };

  const generar = () => {
    setUrl(reportUrl(empresa || undefined, periodos.length ? periodos : undefined));
  };

  const descargar = () => {
    const a = document.createElement("a");
    a.href = reportDownloadUrl(empresa || undefined, periodos.length ? periodos : undefined);
    a.download = "reporte_score.html";
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  const descargarPdf = () => {
    const a = document.createElement("a");
    a.href = reportPdfUrl(empresa || undefined, periodos.length ? periodos : undefined);
    a.download = "reporte_score.pdf";
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  const abrirPestana = () => {
    window.open(reportUrl(empresa || undefined, periodos.length ? periodos : undefined), "_blank");
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Generación de Reportes"
        subtitle="Reportes ejecutivos con gráficas, tomados directamente del dataset. Elige la empresa y los bimestres que deseas incluir."
        icon="📄"
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card>
          <Title>Filtros del reporte</Title>

          <div className="mt-4 space-y-5">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Empresa</label>
              <select
                value={empresa}
                onChange={(e) => setEmpresa(e.target.value)}
                className="w-full rounded-xl border border-brand-200 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm outline-none transition focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
              >
                <option value="">Todas las empresas</option>
                {(opciones?.empresas ?? []).map((e) => (
                  <option key={e} value={e}>
                    {e}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <div className="mb-1 flex items-center justify-between">
                <label className="text-sm font-medium text-slate-700">Bimestres</label>
                <button
                  type="button"
                  onClick={toggleTodos}
                  className="text-xs font-medium text-brand-700 hover:underline"
                >
                  {todosSeleccionados ? "Quitar todos" : "Seleccionar todos"}
                </button>
              </div>
              <div className="max-h-56 space-y-1 overflow-y-auto rounded-xl border border-brand-100 bg-brand-50/30 p-3">
                {(opciones?.periodos ?? []).map((p) => (
                  <label
                    key={p}
                    className="flex cursor-pointer items-center gap-2 rounded-lg px-1 py-0.5 text-sm text-slate-700 transition hover:bg-white"
                  >
                    <input
                      type="checkbox"
                      checked={periodos.includes(p)}
                      onChange={() => togglePeriodo(p)}
                      className="h-4 w-4 rounded border-brand-300 text-brand-600 focus:ring-brand-200"
                    />
                    {p}
                  </label>
                ))}
                {opciones == null && (
                  <Text className="text-slate-400">No se pudo conectar con la API.</Text>
                )}
              </div>
            </div>

            <div className="space-y-2">
              <Button onClick={generar} className="w-full">
                Generar reporte
              </Button>
              <div className="flex gap-2">
                <Button variant="secondary" onClick={abrirPestana} className="flex-1">
                  Abrir en pestaña
                </Button>
                <Button variant="secondary" onClick={descargar} className="flex-1">
                  HTML
                </Button>
                <Button variant="secondary" onClick={descargarPdf} className="flex-1">
                  PDF
                </Button>
              </div>
            </div>
          </div>
        </Card>

        <div className="lg:col-span-2">
          <Card className="h-full">
            <Title>Vista previa</Title>
            {url ? (
              <iframe
                src={url}
                title="Reporte"
                className="mt-4 h-[75vh] w-full rounded-xl border border-brand-100 bg-white"
              />
            ) : (
              <div className="mt-4 flex h-[75vh] items-center justify-center rounded-xl border border-dashed border-brand-200 bg-brand-50/30 text-slate-400">
                Configura los filtros y pulsa “Generar reporte”.
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
