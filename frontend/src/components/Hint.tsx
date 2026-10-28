/**
 * Signo de interrogación con explicación breve al pasar el cursor o enfocar.
 * Sirve para aclarar jerga (rotación, cohorte, mediana) sin recargar la vista.
 */
export default function Hint({ text, arriba = false }: { text: string; arriba?: boolean }) {
  return (
    <span className="group relative inline-flex align-middle">
      <span
        tabIndex={0}
        role="img"
        aria-label={`Ayuda: ${text}`}
        className="ml-1 flex h-4 w-4 cursor-help items-center justify-center rounded-full border border-slate-300 bg-white text-[10px] font-bold leading-none text-slate-500 transition group-hover:border-brand-400 group-hover:text-brand-700 group-focus-within:border-brand-400 group-focus-within:text-brand-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-300"
      >
        ?
      </span>
      <span
        role="tooltip"
        className={`pointer-events-none absolute left-0 z-50 hidden w-56 rounded-lg bg-slate-900 px-3 py-2 text-left text-[11px] font-normal leading-relaxed text-white shadow-lg group-hover:block group-focus-within:block ${
          arriba ? "bottom-full mb-2" : "top-full mt-2"
        }`}
      >
        {text}
      </span>
    </span>
  );
}
