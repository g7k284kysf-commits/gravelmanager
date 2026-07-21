import Link from "next/link";
import { PlanningOverview } from "@/components/planning/planning-overview";

export default function PlanningPage() {
  return (
    <main className="min-h-screen bg-fog"><header className="bg-ink text-white"><div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5"><Link href="/dashboard" className="font-black">GRAVEL<span className="text-gravel">/</span>MANAGER</Link><Link href="/dashboard" className="text-sm font-bold text-white/70">Dashboard</Link></div></header><div className="mx-auto max-w-7xl px-5 py-10"><p className="text-xs font-bold uppercase tracking-[.28em] text-moss/50">Goal management foundation</p><h1 className="mt-3 text-4xl font-black tracking-[-.05em] sm:text-6xl">Season objectives</h1><p className="mt-4 max-w-2xl leading-7 text-moss/60">A lightweight view of hierarchical goals and A/B/C competitions. Full calendar planning follows in a later sprint.</p><div className="mt-10"><PlanningOverview /></div></div></main>
  );
}
