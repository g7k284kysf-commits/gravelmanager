"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { MetricCard } from "@/components/metric-card";
import { DashboardMetrics, getDashboard, getTrainings, Training } from "@/lib/api";

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [trainings, setTrainings] = useState<Training[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getDashboard(), getTrainings()])
      .then(([dashboard, recent]) => { setMetrics(dashboard); setTrainings(recent); })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Unable to load dashboard"));
  }, []);

  const cards = metrics ? [
    ["FTP", metrics.ftp ?? "—", "W"], ["CTL", metrics.ctl, "fitness"], ["ATL", metrics.atl, "fatigue"],
    ["TSB", metrics.tsb, "form"], ["Weekly hours", metrics.weekly_hours, "h"], ["Weekly TSS", metrics.weekly_tss, "pts"],
  ] as const : [];

  return (
    <main className="min-h-screen bg-fog">
      <header className="bg-ink text-white"><div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5"><Link href="/" className="font-black">GRAVEL<span className="text-gravel">/</span>MANAGER</Link><span className="rounded-full bg-white/10 px-4 py-2 text-xs font-bold uppercase tracking-wider">Sprint 1</span></div></header>
      <div className="mx-auto max-w-7xl px-5 py-10">
        <p className="text-xs font-bold uppercase tracking-[.28em] text-moss/50">Performance overview</p>
        <h1 className="mt-3 text-4xl font-black tracking-[-.05em] sm:text-6xl">Your training,<br />in focus.</h1>
        {error && <div role="alert" className="mt-8 rounded-2xl bg-red-50 p-5 text-red-700">{error}. Sign in to connect your data.</div>}
        {!metrics && !error && <div className="mt-8 animate-pulse text-moss/50">Loading your training load…</div>}
        <section aria-label="Training metrics" className="mt-10 grid grid-cols-2 gap-4 lg:grid-cols-3">{cards.map(([label, value, unit], index) => <MetricCard key={label} label={label} value={value} unit={unit} accent={index === 3} />)}</section>
        <section className="mt-12 rounded-[2rem] bg-white p-6 shadow-card sm:p-8">
          <div className="flex items-end justify-between"><div><p className="text-xs font-bold uppercase tracking-[.2em] text-moss/50">Recent work</p><h2 className="mt-2 text-2xl font-black">Latest sessions</h2></div><span className="text-sm font-bold text-moss/50">{trainings.length} rides</span></div>
          <div className="mt-6 divide-y divide-moss/10">{trainings.map((item) => <div key={item.id} className="grid grid-cols-[1fr_auto] gap-3 py-5 sm:grid-cols-[1.4fr_1fr_1fr_auto]"><div><p className="font-bold">{item.sport}</p><p className="text-sm text-moss/50">{item.date}</p></div><p className="hidden self-center text-sm sm:block">{item.distance_km ?? 0} km</p><p className="hidden self-center text-sm sm:block">{item.elevation_m ?? 0} m ↑</p><p className="self-center rounded-full bg-fog px-3 py-1 text-sm font-bold">{item.tss ?? 0} TSS</p></div>)}{trainings.length === 0 && !error && <p className="py-10 text-center text-moss/50">Your first ride will appear here.</p>}</div>
        </section>
      </div>
    </main>
  );
}
