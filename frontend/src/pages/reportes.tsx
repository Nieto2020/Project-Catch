import { useCallback, useEffect, useMemo, useState } from "react";
import { Button, Card, Text, Title } from "@tremor/react";
import {
  getReportOpciones,
  reportDetallePdfUrl,
  reportDetalleUrl,
  reportPdfUrl,
  reportUrl,
  type ReportOpciones,
} from "@/services/api";
import PageHeader from "@/components/PageHeader";

export default function Reportes() {
  const [opciones, setOpciones] = useState<ReportOpciones | null>(null);
  const [cargandoOpciones, setCargandoOpciones] = useState(true);
  const [empresa, setEmpresa] = useState<string>("");
  const [periodos, setPeriodos] = useState<string[]>([]);
  const [tipo, setTipo] = useState<"ejecutivo" | "detallado">("ejecutivo");
  const [url, setUrl] = useState<string>("");

  const cargarOpciones = useCallback(async () => {
    setCargandoOpciones(true);
    // El backend puede estar arrancando: se reintenta antes de mostrar el error.
    for (let intento = 0; intento < 3; intento++) {
      try {
        setOpciones(await getReportOpciones());
        setCargandoOpciones(false);
        return;
      } catch {
        if (intento < 2) await new Promise((r) => setTimeout(r, 1200));
      }
    }
    setOpciones(null);
    setCargandoOpciones(false);
  }, []);

  useEffect(() => {
    cargarOpciones();
  }, [cargarOpciones]);

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

  const urlBase = (emp?: string, per?: string[]) =>
    tipo === "detallado"
      ? reportDetalleUrl(emp, per)
      : reportUrl(emp, per);

  const generar = () => {
    setUrl(urlBase(empresa || undefined, periodos.length ? periodos : undefined));
  };

  const descargar = () => {
    const a = document.createElement("a");
    a.href =
      tipo === "detallado"
        ? reportDetallePdfUrl(empresa || undefined, periodos.length ? periodos : undefined)
        : reportPdfUrl(empresa || undefined, periodos.length ? periodos : undefined);
    a.download = tipo === "detallado" ? "reporte_detallado.pdf" : "reporte_score.pdf";
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Generación de Reportes"
        subtitle="Elige la empresa y los bimestres. El reporte ejecutivo resume la cohorte; el detallado despliega la ficha completa de la empresa con la referencia de su talla."
        icon="📄"
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card>
          <Title>Filtros del reporte</Title>

          <div className="mt-4 space-y-5">
            <div>
              <span className="mb-1 block text-sm font-medium text-slate-700">Tipo de reporte</span>
              <div className="grid grid-cols-2 gap-1 rounded-xl border border-brand-200 bg-brand-50/50 p-1">
                <button
                  type="button"
                  onClick={() => setTipo("ejecutivo")}
                  className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                    tipo === "ejecutivo"
                      ? "bg-white text-brand-700 shadow-sm ring-1 ring-brand-200"
                      : "text-slate-500 hover:text-slate-700"
                  }`}
                >
                  Ejecutivo
                </button>
                <button
                  type="button"
                  onClick={() => setTipo("detallado")}
                  className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                    tipo === "detallado"
                      ? "bg-white text-brand-700 shadow-sm ring-1 ring-brand-200"
                      : "text-slate-500 hover:text-slate-700"
                  }`}
                >
                  Detallado
                </button>
              </div>
            </div>

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
                {cargandoOpciones && (
                  <div className="space-y-2">
                    {[0, 1, 2, 3, 4].map((i) => (
                      <div key={i} className="h-4 animate-pulse rounded bg-slate-200/70" />
                    ))}
                  </div>
                )}
                {!cargandoOpciones && opciones == null && (
                  <div className="space-y-2">
                    <Text className="text-slate-400">No se pudo conectar con la API.</Text>
                    <button
                      type="button"
                      onClick={cargarOpciones}
                      className="text-xs font-medium text-brand-700 hover:underline"
                    >
                      Reintentar
                    </button>
                  </div>
                )}
              </div>
            </div>

            <div className="space-y-2">
              <Button onClick={descargar} className="w-full">
                Descargar reporte (PDF)
              </Button>
              <Button variant="secondary" onClick={generar} className="w-full">
                Ver reporte aquí
              </Button>
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
                Configura los filtros y pulsa “Ver reporte aquí”.
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
