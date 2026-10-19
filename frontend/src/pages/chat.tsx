import { useEffect, useRef, useState } from "react";
import { Badge, Button, Card, Text, Title } from "@tremor/react";
import { useAppStore } from "@/store/useAppStore";

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
    <div className="flex h-[calc(100vh-4rem)] flex-col space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Asistente IA</h1>
          <p className="text-sm text-slate-500">
            Consulta la encuesta en lenguaje natural · agente sobre el DataFrame en memoria
          </p>
        </div>
        <Button variant="secondary" onClick={resetChat} disabled={chat.length === 0}>
          Limpiar
        </Button>
      </div>

      <Card className="flex-1 overflow-y-auto">
        {chat.length === 0 && (
          <div className="space-y-3 py-6">
            <Text className="text-center">Pregúntame sobre los datos de RH. Por ejemplo:</Text>
            <div className="flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => submit(s)}
                  className="rounded-full border border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100"
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
                className={`max-w-[80%] rounded-xl px-4 py-3 text-sm whitespace-pre-wrap ${
                  m.role === "user"
                    ? "bg-cyan-600 text-white"
                    : "bg-slate-100 text-slate-800"
                }`}
              >
                {m.engine && (
                  <Badge size="xs" className="mb-1 block w-fit">
                    {m.engine === "llm" ? "LLM (OpenAI)" : "modo local"}
                  </Badge>
                )}
                {m.content}
              </div>
            </div>
          ))}
          {chatLoading && (
            <div className="flex justify-start">
              <div className="rounded-xl bg-slate-100 px-4 py-3 text-sm text-slate-500">
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
          className="flex-1 rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm"
        />
        <Button type="submit" disabled={chatLoading || !input.trim()}>
          Enviar
        </Button>
      </form>
    </div>
  );
}
