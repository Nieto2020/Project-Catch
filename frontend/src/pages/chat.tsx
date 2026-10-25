import { useEffect, useRef, useState } from "react";
import { Badge, Button, Card, Text } from "@tremor/react";
import { useAppStore } from "@/store/useAppStore";
import PageHeader from "@/components/PageHeader";

const SUGGESTIONS = [
  "¿Cuántas empresas hay?",
  "¿Cuál es la rotación bimestral promedio?",
  "¿Cuál es el salario inicial promedio?",
  "Top 5 empresas por competitividad",
  "¿Cuál es el promedio de faltas por cada 100 empleados?",
];

export default function Chat() {
  const { chat, chatLoading, sendChat, resetChat } = useAppStore();
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

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
          subtitle="Consulta la encuesta en lenguaje natural · agente sobre el DataFrame en memoria"
          icon="🤖"
        />
        <Button
          variant="secondary"
          onClick={resetChat}
          disabled={chat.length === 0}
          className="mt-2 shrink-0"
        >
          Limpiar
        </Button>
      </div>

      <Card className="flex-1 overflow-y-auto">
        {chat.length === 0 && (
          <div className="space-y-4 py-6">
            <Text className="text-center">Pregúntame sobre los datos de RH. Por ejemplo:</Text>
            <div className="flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => submit(s)}
                  className="rounded-full border border-brand-200 bg-white px-4 py-1.5 text-sm text-brand-700 shadow-sm transition hover:border-brand-400 hover:bg-brand-50"
                >
                  {s}
                </button>
              ))}
            </div>
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
                {m.engine && (
                  <Badge
                    size="xs"
                    color={m.role === "user" ? "blue" : "sky"}
                    className="mb-1 block w-fit"
                  >
                    {m.engine === "llm" ? "LLM" : "modo local"}
                  </Badge>
                )}
                {m.content}
              </div>
            </div>
          ))}
          {chatLoading && (
            <div className="flex justify-start">
              <div className="flex items-center gap-2 rounded-2xl bg-brand-50 px-4 py-3 text-sm text-slate-500 ring-1 ring-brand-100">
                <span className="h-2 w-2 animate-pulse rounded-full bg-brand-500" />
                Pensando…
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
        className="flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Escribe tu pregunta…"
          className="flex-1 rounded-xl border border-brand-200 bg-white px-4 py-3 text-sm shadow-sm outline-none transition placeholder:text-slate-400 focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
        />
        <Button type="submit" disabled={chatLoading || !input.trim()}>
          Enviar
        </Button>
      </form>
    </div>
  );
}
