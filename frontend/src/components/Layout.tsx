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
    <div className="min-h-screen bg-blue-50/40 text-slate-800">
      <aside className="fixed inset-y-0 left-0 z-20 flex w-64 flex-col border-r border-blue-100 bg-white">
        <div className="border-b border-blue-100 px-6 py-6">
          <div className="flex items-center gap-3">
            <img
              src="/logo-cc-moneda.png"
              alt="Catch Consulting"
              className="h-9 w-9 rounded-full opacity-90"
            />
            <div>
              <p className="text-sm font-bold text-blue-800">SCORE</p>
              <p className="mt-0.5 text-[11px] leading-tight text-slate-500">
                Smart Catch Optimization &amp; Retention Ecosystem
              </p>
            </div>
          </div>
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
                    ? "bg-blue-100 text-blue-900"
                    : "text-slate-600 hover:bg-blue-50 hover:text-blue-800"
                }`}
              >
                <span aria-hidden>{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-blue-100 px-6 py-4 text-xs text-slate-400">
          Prototipo para pitch · Datatón
        </div>
      </aside>

      <main className="ml-64 min-h-screen">
        <div className="mx-auto max-w-7xl px-8 py-8">{children}</div>
      </main>
    </div>
  );
}
