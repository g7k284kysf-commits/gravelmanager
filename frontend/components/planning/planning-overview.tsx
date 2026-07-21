"use client";

import { useEffect, useState } from "react";
import { PriorityBadge } from "@/components/planning/priority-badge";
import { getCompetitions, getGoals, type Competition, type Goal } from "@/lib/api";

export function PlanningOverview() {
  const [goals, setGoals] = useState<Goal[] | null>(null);
  const [competitions, setCompetitions] = useState<Competition[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getGoals(), getCompetitions()])
      .then(([nextGoals, nextCompetitions]) => { setGoals(nextGoals); setCompetitions(nextCompetitions); })
      .catch(() => setError("Planning data could not be loaded."));
  }, []);

  if (error) return <p role="alert" className="rounded-2xl bg-red-50 p-5 text-red-800">{error}</p>;
  if (!goals || !competitions) return <div role="status" aria-label="Loading planning" className="h-64 animate-pulse rounded-[2rem] bg-white/70" />;

  const roots = goals.filter((goal) => goal.parent_goal_id === null);
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <section className="rounded-[2rem] bg-white p-6 shadow-card"><h2 className="text-2xl font-black">Goals</h2><div className="mt-5 space-y-4">{roots.map((goal) => <div key={goal.id} className="rounded-2xl bg-fog p-4"><p className="font-black">{goal.title}</p><p className="mt-1 text-xs uppercase tracking-wider text-moss/50">{goal.goal_type.replaceAll("_", " ")} · {goal.priority}</p>{goals.filter((child) => child.parent_goal_id === goal.id).map((child) => <div key={child.id} className="mt-3 border-l-2 border-gravel pl-4 text-sm font-bold">{child.title}</div>)}</div>)}{!roots.length && <p className="py-8 text-sm text-moss/50">No goals yet. Use the planning API to create the season foundation.</p>}</div></section>
      <section className="rounded-[2rem] bg-white p-6 shadow-card"><h2 className="text-2xl font-black">Competitions</h2><div className="mt-5 divide-y divide-moss/10">{competitions.map((competition) => <div key={competition.id} className="flex items-center gap-4 py-4"><PriorityBadge priority={competition.race_priority} /><div><p className="font-black">{competition.name}</p><p className="text-sm text-moss/50">{competition.start_date}{competition.discipline ? ` · ${competition.discipline}` : ""}</p></div></div>)}{!competitions.length && <p className="py-8 text-sm text-moss/50">No competitions planned yet.</p>}</div></section>
    </div>
  );
}
