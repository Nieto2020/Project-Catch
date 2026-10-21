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
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <aside className="fixed inset-y-0 left-0 z-20 flex w-64 flex-col bg-slate-900 text-slate-100">
        <div className="border-b border-slate-700 px-6 py-6">
          <p className="text-xs font-semibold uppercase tracking-widest text-cyan-400">SCORE</p>
          <p className="mt-1 text-sm text-slate-400">
            Smart Catch Optimization &amp; Retention Ecosystem
          </p>
        </div>
        <nav className="flex-1 space-y-1 px-3 py-4">
          {NAV.map((item) => {
            const active = router.pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 rounded-lg px-4 py-2.5 text-sm font-medium transition ${
                  active
                    ? "bg-cyan-600 text-white"
                    : "text-slate-300 hover:bg-slate-800 hover:text-white"
                }`}
              >
                <span aria-hidden>{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-slate-700 px-6 py-4 text-xs text-slate-500">
          Prototipo para pitch · Datatón
        </div>
      </aside>

      <main className="ml-64 min-h-screen">
        <div className="mx-auto max-w-7xl px-8 py-8">{children}</div>
      </main>
    </div>
  );
}
