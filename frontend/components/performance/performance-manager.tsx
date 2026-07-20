"use client";

import { useEffect, useState } from "react";
import { MetricCard } from "@/components/metric-card";
import { PerformanceChart } from "@/components/performance/performance-chart";
import {
  getPerformanceChart,
  getPerformanceSummary,
  type PerformanceChartResponse,
  type PerformanceRange,
  type PerformanceSummary,
} from "@/lib/api";

const ranges: PerformanceRange[] = ["28d", "90d", "180d", "365d"];

function LoadingState() {
  return (
    <div role="status" className="space-y-5" aria-label="Loading performance data">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {Array.from({ length: 8 }, (_, index) => (
          <div key={index} className="h-32 animate-pulse rounded-3xl bg-white/70" />
        ))}
      </div>
      <div className="h-[22rem] animate-pulse rounded-[2rem] bg-white/70" />
    </div>
  );
}

export function PerformanceManager() {
  const [range, setRange] = useState<PerformanceRange>("90d");
  const [summary, setSummary] = useState<PerformanceSummary | null>(null);
  const [chart, setChart] = useState<PerformanceChartResponse | null>(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    let active = true;
    setError("");
    Promise.all([getPerformanceSummary(), getPerformanceChart(range)])
      .then(([nextSummary, nextChart]) => {
        if (active) {
          setSummary(nextSummary);
          setChart(nextChart);
        }
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(reason instanceof Error ? reason.message : "Unable to load performance data");
        }
      });
    return () => { active = false; };
  }, [range, retry]);

  if (error) {
    return (
      <section className="mt-12 rounded-[2rem] bg-white p-8 shadow-card" aria-labelledby="performance-title">
        <h2 id="performance-title" className="text-2xl font-black">Performance Manager</h2>
        <div role="alert" className="mt-5 rounded-2xl bg-red-50 p-5 text-red-800">
          <p className="font-bold">Performance data could not be loaded.</p>
          <p className="mt-1 text-sm">{error}</p>
          <button type="button" onClick={() => setRetry((value) => value + 1)} className="mt-4 rounded-full bg-ink px-5 py-2 text-sm font-bold text-white">Try again</button>
        </div>
      </section>
    );
  }

  if (!summary || !chart) {
    return <section className="mt-12"><LoadingState /></section>;
  }

  const cards = [
    ["CTL", summary.ctl, "fitness"],
    ["ATL", summary.atl, "fatigue"],
    ["TSB", summary.tsb, "form"],
    ["Ramp rate", summary.ramp_rate, "7d"],
    ["7-day TSS", summary.seven_day_tss, "pts"],
    ["28-day TSS", summary.twenty_eight_day_tss, "pts"],
    ["7-day hours", summary.seven_day_training_hours, "h"],
    ["28d CTL change", summary.twenty_eight_day_ctl_change, "pts"],
  ] as const;

  return (
    <section className="mt-12" aria-labelledby="performance-title">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[.2em] text-moss/50">Training load</p>
          <h2 id="performance-title" className="mt-2 text-3xl font-black tracking-[-.04em]">Performance Manager</h2>
        </div>
        <div className="flex w-full overflow-x-auto rounded-full bg-white p-1 shadow-card sm:w-auto" aria-label="Chart range">
          {ranges.map((option) => (
            <button
              key={option}
              type="button"
              aria-pressed={range === option}
              onClick={() => setRange(option)}
              className={`min-w-16 flex-1 rounded-full px-4 py-2 text-xs font-black uppercase transition sm:flex-none ${range === option ? "bg-ink text-white" : "text-moss/60 hover:text-ink"}`}
            >
              {option}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-7 grid grid-cols-2 gap-4 lg:grid-cols-4">
        {cards.map(([label, value, unit], index) => (
          <MetricCard key={label} label={label} value={value.toFixed(1)} unit={unit} accent={index === 2} />
        ))}
      </div>

      <div className="mt-6 rounded-[2rem] bg-white p-4 shadow-card sm:p-7">
        {chart.points.length ? (
          <PerformanceChart points={chart.points} />
        ) : (
          <div className="flex h-[22rem] flex-col items-center justify-center px-6 text-center">
            <div className="grid h-14 w-14 place-items-center rounded-full bg-gravel text-2xl" aria-hidden="true">↗</div>
            <h3 className="mt-5 text-xl font-black">Build your performance curve</h3>
            <p className="mt-2 max-w-md text-sm leading-6 text-moss/60">Add your first training session to calculate fitness, fatigue and form across continuous calendar days.</p>
          </div>
        )}
      </div>
    </section>
  );
}
