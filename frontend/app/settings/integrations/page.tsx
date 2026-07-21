import Link from "next/link";
import { IntegrationManager } from "@/components/integrations/integration-manager";

export default function IntegrationsPage() {
  return (
    <main className="min-h-screen bg-fog">
      <header className="bg-ink text-white"><div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5"><Link href="/dashboard" className="font-black">GRAVEL<span className="text-gravel">/</span>MANAGER</Link><Link href="/dashboard" className="text-sm font-bold text-white/70">Dashboard</Link></div></header>
      <div className="mx-auto max-w-7xl px-5 py-10">
        <p className="text-xs font-bold uppercase tracking-[.28em] text-moss/50">Settings</p>
        <h1 className="mt-3 text-4xl font-black tracking-[-.05em] sm:text-6xl">Integrations</h1>
        <p className="mt-4 max-w-2xl leading-7 text-moss/60">Control where your data comes from. Live provider access is clearly separated from manual file imports.</p>
        <div className="mt-10"><IntegrationManager /></div>
      </div>
    </main>
  );
}
