import Link from "next/link";
import { useRouter } from "next/router";
import type { ReactNode } from "react";

const NAV = [
  { href: "/", label: "Barómetro Global", icon: "⚖️" },
  { href: "/chat", label: "Asistente IA", icon: "🤖" },
  { href: "/video", label: "Video Descriptivo", icon: "🎬" },
  { href: "/reportes", label: "Reportes", icon: "📄" },
];

export default function Layout({ children }: { children: ReactNode }) {
  const router = useRouter();

  return (
    <div className="min-h-screen font-sans text-slate-800">
      <aside className="fixed inset-y-0 left-0 z-20 flex w-64 flex-col border-r border-brand-100 bg-white shadow-soft">
        <div className="border-b border-brand-100 px-6 py-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br from-brand-50 to-brand-100 ring-1 ring-brand-100">
              <img
                src="/logo-cc-moneda.png"
                alt="Catch Consulting"
                className="h-7 w-7 object-contain"
              />
            </div>
            <div className="min-w-0">
              <p className="text-base font-bold tracking-tight text-brand-900">SCORE</p>
              <p className="mt-0.5 truncate text-[11px] leading-tight text-slate-500">
                Smart Catch Optimization &amp; Retention Ecosystem
              </p>
            </div>
          </div>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-5">
          <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-400">
            Módulos
          </p>
          {NAV.map((item) => {
            const active = router.pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`group flex items-center gap-3 rounded-xl px-4 py-2.5 text-sm font-medium transition ${
                  active
                    ? "bg-gradient-to-r from-brand-700 to-brand-600 text-white shadow-soft"
                    : "text-slate-600 hover:bg-brand-50 hover:text-brand-800"
                }`}
              >
                <span
                  className={`flex h-7 w-7 items-center justify-center rounded-lg text-sm ${
                    active ? "bg-white/15" : "bg-brand-50 text-slate-500 group-hover:bg-brand-100"
                  }`}
                  aria-hidden
                >
                  {item.icon}
                </span>
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-brand-100 px-6 py-4">
          <div className="rounded-xl bg-gradient-to-br from-brand-50 to-white px-4 py-3 ring-1 ring-brand-100">
            <p className="text-xs font-semibold text-brand-800">Catch Consulting</p>
            <p className="mt-0.5 text-[11px] text-slate-400">Prototipo para pitch · Datatón</p>
          </div>
        </div>
      </aside>

      <main className="ml-64 min-h-screen">
        <div className="mx-auto max-w-7xl px-8 py-8">{children}</div>
      </main>
    </div>
  );
}
