import { Badge, Button, Card, Metric, Text, Title } from "@tremor/react";

const PLANES = [
  {
    nombre: "Básico",
    precio: "$9,900",
    descripcion: "Para empresas que inician su estrategia de retención.",
    destacado: false,
    features: [
      "Dashboard descriptivo mensual",
      "KPIs de rotación y ausentismo",
      "Reporte PDF ejecutivo",
      "Histórico de 2 bimestres",
    ],
  },
  {
    nombre: "Intermedio",
    precio: "$19,900",
    descripcion: "Analítica predictiva y simulación de escenarios.",
    destacado: true,
    features: [
      "Todo lo del plan Básico",
      "Modelo predictivo de rotación",
      "Simulador What-If",
      "Barómetro de competitividad",
      "Alertas automáticas",
      "Histórico completo (7 bimestres)",
    ],
  },
  {
    nombre: "Premium",
    precio: "$29,900",
    descripcion: "Inteligencia artificial conversacional sobre tus datos.",
    destacado: false,
    features: [
      "Todo lo del plan Intermedio",
      "Asistente IA (lenguaje natural)",
      "Benchmarking por industria",
      "Soporte prioritario",
      "Implementación asistida",
    ],
  },
];

export default function Comercial() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Capa Comercial</h1>
        <p className="text-sm text-slate-500">
          Niveles de suscripción conceptuales para el pitch de SCORE.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {PLANES.map((p) => (
          <Card
            key={p.nombre}
            decoration="top"
            decorationColor={p.destacado ? "cyan" : "slate"}
            className={p.destacado ? "ring-2 ring-cyan-500" : ""}
          >
            <div className="flex items-center justify-between">
              <Title>{p.nombre}</Title>
              {p.destacado && <Badge color="cyan">Recomendado</Badge>}
            </div>
            <div className="mt-3">
              <Metric>{p.precio}</Metric>
              <Text className="mt-1">MXN / bimestre</Text>
            </div>
            <Text className="mt-3">{p.descripcion}</Text>
            <ul className="mt-4 space-y-2">
              {p.features.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm text-slate-600">
                  <span className="mt-0.5 text-cyan-600">✓</span>
                  {f}
                </li>
              ))}
            </ul>
            <Button className="mt-6 w-full" variant={p.destacado ? "primary" : "secondary"}>
              Solicitar demo
            </Button>
          </Card>
        ))}
      </div>

      <Card>
        <Title>Mensaje para inversionistas</Title>
        <Text className="mt-2 leading-relaxed">
          SCORE convierte los datos históricos de RH en decisiones accionables: describe el estado
          actual, predice la rotación y prescribe acciones (subir salarios, invertir en
          capacitación o reducir ausentismo) con un retorno medible en retención de talento.
        </Text>
      </Card>
    </div>
  );
}
