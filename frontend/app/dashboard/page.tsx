"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { MetricCard } from "@/components/metric-card";
import { PerformanceManager } from "@/components/performance/performance-manager";
import { DashboardMetrics, getDashboard, getTrainings, Training } from "@/lib/api";

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [trainings, setTrainings] = useState<Training[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getDashboard(), getTrainings()])
      .then(([dashboard, recent]) => {
        setMetrics(dashboard);
        setTrainings(recent);
      })
      .catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : "Unable to load dashboard"),
      );
  }, []);

  return (
    <main className="min-h-screen bg-fog">
      <header className="bg-ink text-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5">
          <Link href="/" className="font-black">GRAVEL<span className="text-gravel">/</span>MANAGER</Link>
          <span className="rounded-full bg-white/10 px-4 py-2 text-xs font-bold uppercase tracking-wider">Sprint 2</span>
        </div>
      </header>
      <div className="mx-auto max-w-7xl px-5 py-10">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[.28em] text-moss/50">Performance overview</p>
            <h1 className="mt-3 text-4xl font-black tracking-[-.05em] sm:text-6xl">Your training,<br />in focus.</h1>
          </div>
          {metrics && <div className="w-full sm:w-52"><MetricCard label="Current FTP" value={metrics.ftp ?? "—"} unit="W" /></div>}
        </div>
        {error && <div role="alert" className="mt-8 rounded-2xl bg-red-50 p-5 text-red-700">{error}. Sign in to connect your data.</div>}
        {!metrics && !error && <div className="mt-8 animate-pulse text-moss/50">Loading your athlete profile…</div>}

        <PerformanceManager />

        <section className="mt-12 rounded-[2rem] bg-white p-6 shadow-card sm:p-8">
          <div className="flex items-end justify-between">
            <div><p className="text-xs font-bold uppercase tracking-[.2em] text-moss/50">Recent work</p><h2 className="mt-2 text-2xl font-black">Latest sessions</h2></div>
            <span className="text-sm font-bold text-moss/50">{trainings.length} rides</span>
          </div>
          <div className="mt-6 divide-y divide-moss/10">
            {trainings.map((item) => (
              <div key={item.id} className="grid grid-cols-[1fr_auto] gap-3 py-5 sm:grid-cols-[1.4fr_1fr_1fr_auto]">
                <div><p className="font-bold">{item.sport}</p><p className="text-sm text-moss/50">{item.date}</p></div>
                <p className="hidden self-center text-sm sm:block">{item.distance_km ?? 0} km</p>
                <p className="hidden self-center text-sm sm:block">{item.elevation_m ?? 0} m ↑</p>
                <p className="self-center rounded-full bg-fog px-3 py-1 text-sm font-bold">{item.tss ?? 0} TSS</p>
              </div>
            ))}
            {trainings.length === 0 && !error && <p className="py-10 text-center text-moss/50">Your first ride will appear here.</p>}
          </div>
        </section>
      </div>
    </main>
  );
}
