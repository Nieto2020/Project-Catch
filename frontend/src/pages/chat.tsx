import { useEffect, useRef, useState } from "react";
import { Badge, Button, Card, Text } from "@tremor/react";
import { useAppStore } from "@/store/useAppStore";
import PageHeader from "@/components/PageHeader";

export default function Chat() {
  const {
    chat,
    chatLoading,
    chatEstado,
    sugerencias,
    chatContexto,
    sendChat,
    enviarRapida,
    setChatContexto,
    loadChatEstado,
    resetChat,
  } = useAppStore();
  const [input, setInput] = useState("");
  const [elapsed, setElapsed] = useState(0);
  // Colapsadas por defecto: la conversación manda y el panel no empuja el
  // formulario fuera de la vista; se despliegan con un clic.
  const [sugerenciasAbiertas, setSugerenciasAbiertas] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Contador visible mientras el modelo responde.
  useEffect(() => {
    if (!chatLoading) {
      setElapsed(0);
      return;
    }
    const timer = setInterval(() => setElapsed((v) => v + 1), 1000);
    return () => clearInterval(timer);
  }, [chatLoading]);

  useEffect(() => {
    loadChatEstado();
  }, [loadChatEstado]);

  // Al llegar desde el ranking con un contexto, se deja lista una pregunta.
  useEffect(() => {
    if (!chatContexto) return;
    setInput((prev) =>
      prev.trim() ? prev : "¿Qué acciones recomendarías para mejorar el desempeño de esta empresa?",
    );
    inputRef.current?.focus();
  }, [chatContexto]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat, chatLoading]);

  const submit = (text?: string) => {
    const msg = (text ?? input).trim();
    if (!msg || chatLoading) return;
    setInput("");
    sendChat(msg);
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col gap-4">
      <div className="flex items-start justify-between gap-6">
        <PageHeader
          title="Asistente IA"
          subtitle="Consulta la encuesta en lenguaje natural con el modelo de lenguaje"
          icon="🤖"
        />
        <div className="mt-2 flex shrink-0 items-center gap-2">
          <Badge color={chatEstado?.llm_disponible ? "blue" : "slate"} size="sm">
            {chatEstado?.llm_disponible
              ? `Modelo: ${chatEstado.modelo}`
              : "Modelo no configurado"}
          </Badge>
          <Button variant="secondary" onClick={resetChat} disabled={chat.length === 0}>
            Limpiar
          </Button>
        </div>
      </div>

      {sugerencias.length > 0 && (
        <div className="rounded-xl border border-brand-100 bg-white/70 px-4 py-2 shadow-soft backdrop-blur">
          <button
            type="button"
            onClick={() => setSugerenciasAbiertas((abiertas) => !abiertas)}
            aria-expanded={sugerenciasAbiertas}
            aria-controls="respuestas-rapidas"
            title={
              sugerenciasAbiertas
                ? "Ocultar las respuestas rápidas"
                : "Mostrar las respuestas rápidas"
            }
            className="group flex w-full items-center gap-2 rounded-lg text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-300"
          >
            <svg
              aria-hidden
              viewBox="0 0 20 20"
              fill="currentColor"
              className={`h-3.5 w-3.5 shrink-0 text-slate-400 transition-transform duration-200 group-hover:text-brand-600 ${
                sugerenciasAbiertas ? "rotate-180" : ""
              }`}
            >
              <path
                fillRule="evenodd"
                d="M5.23 7.21a.75.75 0 0 1 1.06.02L10 11.17l3.71-3.94a.75.75 0 1 1 1.08 1.04l-4.25 4.5a.75.75 0 0 1-1.08 0l-4.25-4.5a.75.75 0 0 1 .02-1.06Z"
                clipRule="evenodd"
              />
            </svg>
            <span className="text-[11px] font-semibold uppercase tracking-widest text-slate-400 transition group-hover:text-brand-700">
              Respuestas rápidas
            </span>
            <span className="rounded-full bg-brand-50 px-1.5 py-0.5 text-[10px] font-semibold leading-none text-brand-700 ring-1 ring-brand-100">
              {sugerencias.length}
            </span>
            <span className="hidden text-[11px] text-slate-400 sm:inline">
              sin consumir el modelo
            </span>
            <span className="ml-auto text-[11px] font-medium text-slate-400 transition group-hover:text-brand-600">
              {sugerenciasAbiertas ? "Ocultar" : "Mostrar"}
            </span>
          </button>
          {sugerenciasAbiertas && (
            <div id="respuestas-rapidas" className="mt-2 flex flex-wrap gap-2">
              {sugerencias.map((s) => (
                <button
                  key={s.pregunta}
                  onClick={() => enviarRapida(s)}
                  disabled={chatLoading}
                  title={s.respuesta}
                  className="rounded-full border border-brand-200 bg-white px-4 py-1.5 text-sm text-brand-700 shadow-sm transition hover:border-brand-400 hover:bg-brand-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {s.pregunta}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      <Card className="flex-1 overflow-y-auto">
        {chat.length === 0 && (
          <div className="space-y-3 py-10 text-center">
            <Text className="text-slate-500">
              Pregunta lo que quieras sobre los datos de RH, o usa una respuesta rápida.
            </Text>
            <Text className="text-xs text-slate-400">
              Las respuestas rápidas se calculan al instante desde el dataset; el resto lo responde
              el modelo de lenguaje.
            </Text>
          </div>
        )}

        <div className="space-y-4">
          {chat.map((m, i) => (
            <div
              key={i}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap shadow-sm ${
                  m.role === "user"
                    ? "bg-gradient-to-br from-brand-700 to-brand-600 text-white"
                    : "bg-brand-50 text-slate-700 ring-1 ring-brand-100"
                }`}
              >
                {m.role === "assistant" && (
                  <div className="mb-1">
                    <span title={m.motivo}>
                      <Badge size="xs" color={m.kind === "rapida" ? "slate" : "blue"}>
                        {m.kind === "rapida" ? "Respuesta rápida" : "Modelo"}
                      </Badge>
                    </span>
                  </div>
                )}
                {m.content}
              </div>
            </div>
          ))}
          {chatLoading && (
            <div className="flex justify-start">
              <div className="flex items-center gap-2 rounded-2xl bg-brand-50 px-4 py-3 text-sm text-slate-500 ring-1 ring-brand-100">
                <span className="h-2 w-2 animate-pulse rounded-full bg-brand-500" />
                <span>
                  Consultando el modelo…
                  {elapsed > 0 && <span className="text-slate-400"> {elapsed}s</span>}
                </span>
                {elapsed >= 20 && (
                  <span className="text-xs text-slate-400">
                    (el agente está analizando el dataset)
                  </span>
                )}
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </Card>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className="space-y-2"
      >
        {chatContexto && (
          <div className="rounded-xl border border-brand-200 bg-brand-50/70 px-4 py-3 shadow-soft ring-1 ring-brand-100">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-widest text-brand-700">
                  <span aria-hidden>✨</span> Contexto adjunto del ranking
                </p>
                <p className="mt-1 whitespace-pre-line text-xs leading-relaxed text-slate-600">
                  {chatContexto}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setChatContexto(null)}
                title="Quitar contexto"
                aria-label="Quitar contexto"
                className="shrink-0 rounded-lg px-2 py-1 text-xs font-medium text-slate-400 transition hover:bg-white hover:text-rose-500"
              >
                Quitar
              </button>
            </div>
          </div>
        )}
        <div className="flex gap-2">
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Escribe tu pregunta para el modelo…"
            className="flex-1 rounded-xl border border-brand-200 bg-white px-4 py-3 text-sm shadow-sm outline-none transition placeholder:text-slate-400 focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
          />
          <Button type="submit" disabled={chatLoading || !input.trim()}>
            Enviar
          </Button>
        </div>
      </form>
    </div>
  );
}

