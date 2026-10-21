import { useEffect } from "react";
import { Badge, Button, Callout, Card, Text, Title } from "@tremor/react";
import { useAppStore } from "@/store/useAppStore";
import { videoDownloadUrl } from "@/services/api";

const fmtDuration = (s: number | null) => {
  if (s == null) return "—";
  const m = Math.floor(s / 60);
  const r = Math.round(s % 60);
  return `${m}:${r.toString().padStart(2, "0")}`;
};

export default function VideoPage() {
  const { video, videoInfo, videoLoading, videoError, loadVideoInfo, generateVideo } =
    useAppStore();

  useEffect(() => {
    loadVideoInfo();
  }, [loadVideoInfo]);

  const disponible = videoInfo?.disponible ?? false;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Video Descriptivo</h1>
        <p className="text-sm text-slate-500">
          Genera un video de 1 a 3 minutos con voz natural (sin avatar) que narra los hallazgos
          del análisis y muestra las gráficas clave.
        </p>
      </div>

      {videoError && (
        <Callout title="Error al generar el video" color="rose">
          {videoError}
        </Callout>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <Title>Video</Title>
          <div className="mt-4 flex items-center gap-3">
            <Button onClick={generateVideo} loading={videoLoading} disabled={videoLoading}>
              {disponible ? "Regenerar video" : "Generar video"}
            </Button>
            {videoInfo?.voz && <Badge color="cyan">Voz: {videoInfo.voz}</Badge>}
          </div>

          <div className="mt-6">
            {disponible ? (
              <video controls className="w-full rounded-lg border border-slate-200">
                <source src={videoDownloadUrl()} type="video/mp4" />
                Tu navegador no soporta video HTML5.
              </video>
            ) : (
              <div className="rounded-lg border border-dashed border-slate-300 py-16 text-center text-slate-400">
                {videoLoading
                  ? "Generando el video… (puede tardar alrededor de un minuto)"
                  : "Aún no hay video. Pulsa “Generar video”."}
              </div>
            )}
          </div>

          {video && (
            <div className="mt-4 flex items-center justify-between">
              <Text>
                Duración: <b>{fmtDuration(video.duracion_segundos)}</b>
              </Text>
              <a href={videoDownloadUrl()} download className="text-sm font-medium text-cyan-600 hover:underline">
                Descargar MP4
              </a>
            </div>
          )}
        </Card>

        <Card>
          <Title>Hallazgos del análisis</Title>
          <div className="mt-4 space-y-3">
            {(videoInfo?.hallazgos ?? video?.hallazgos ?? []).map((h, i) => (
              <div key={i} className="rounded-lg bg-slate-50 p-3">
                <Text className="font-semibold">
                  {i + 1}. {h.titulo}
                </Text>
                <Text className="mt-1 text-slate-600">{h.narracion}</Text>
              </div>
            ))}
            {!disponible && !videoLoading && (
              <Text className="text-slate-400">
                Los hallazgos aparecerán aquí tras generar el video.
              </Text>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
