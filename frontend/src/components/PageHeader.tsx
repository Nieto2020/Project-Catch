import type { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  icon?: ReactNode;
}

/**
 * Cabecera consistente de página: gradiente azul en el título, subtítulo
 * descriptivo y un chip de icono opcional.
 */
export default function PageHeader({ title, subtitle, icon }: PageHeaderProps) {
  return (
    <div className="mb-8 flex items-start justify-between gap-6">
      <div>
        <h1 className="bg-gradient-to-r from-brand-900 via-brand-700 to-brand-500 bg-clip-text text-3xl font-bold tracking-tight text-transparent">
          {title}
        </h1>
        {subtitle && (
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-500">{subtitle}</p>
        )}
      </div>
      {icon && (
        <div className="hidden h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-600 to-brand-800 text-2xl text-white shadow-card sm:flex">
          {icon}
        </div>
      )}
    </div>
  );
}
