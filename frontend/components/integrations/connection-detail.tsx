"use client";

import { useCallback, useEffect, useState } from "react";
import { StatusBadge } from "@/components/integrations/status-badge";
import {
  getConnection,
  getIntegrationEvents,
  getProviders,
  getSyncs,
  revokeConnection,
  startConnectionSync,
  testConnection,
  type IntegrationConnection,
  type IntegrationEvent,
  type IntegrationSync,
  type Provider,
} from "@/lib/api";

export function ConnectionDetail({ connectionId }: { connectionId: number }) {
  const [connection, setConnection] = useState<IntegrationConnection | null>(null);
  const [syncs, setSyncs] = useState<IntegrationSync[]>([]);
  const [events, setEvents] = useState<IntegrationEvent[]>([]);
  const [provider, setProvider] = useState<Provider | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [nextConnection, allSyncs, allEvents, providers] = await Promise.all([
        getConnection(connectionId),
        getSyncs(connectionId),
        getIntegrationEvents(connectionId),
        getProviders(),
      ]);
      setConnection(nextConnection);
      setSyncs(allSyncs);
      setEvents(allEvents);
      setProvider(
        providers.find((item) => item.provider_key === nextConnection.provider_key) ?? null,
      );
    } catch {
      setError("This connection could not be loaded.");
    }
  }, [connectionId]);

  useEffect(() => { void load(); }, [load]);

  async function test() {
    setMessage("Testing…");
    try { setMessage((await testConnection(connectionId)).message); }
    catch { setMessage("Connection test failed safely. No credentials were exposed."); }
  }

  async function sync() {
    setMessage("Starting synchronization…");
    try { await startConnectionSync(connectionId); setMessage("Synchronization started."); await load(); }
    catch { setMessage("Manual synchronization is not available for this provider yet."); }
  }

  async function revoke() {
    if (!window.confirm("Revoke this connection and remove its stored credentials?")) return;
    try { setConnection(await revokeConnection(connectionId)); setMessage("Connection revoked."); }
    catch { setMessage("The connection could not be revoked."); }
  }

  if (error) return <p role="alert" className="rounded-2xl bg-red-50 p-5 text-red-800">{error}</p>;
  if (!connection) return <div role="status" aria-label="Loading connection" className="h-64 animate-pulse rounded-[2rem] bg-white/70" />;

  const active = connection.status === "connected";
  const canTest = active && provider?.operational === true;
  const canSync = canTest && provider.capabilities.includes("polling");

  return (
    <div className="space-y-6">
      <section className="rounded-[2rem] bg-white p-6 shadow-card sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-[.2em] text-moss/50">{connection.provider_key}</p><h1 className="mt-2 text-3xl font-black">{connection.display_name}</h1></div><StatusBadge status={connection.status} /></div>
        <p className="mt-5 text-sm text-moss/60">Last successful sync: {connection.last_successful_sync_at ? new Date(connection.last_successful_sync_at).toLocaleString() : "Never"}</p>
        {connection.last_error_message && <p className="mt-3 rounded-xl bg-red-50 p-4 text-sm text-red-800">{connection.last_error_message}</p>}
        {provider && !provider.operational && <p className="mt-4 text-sm font-bold text-amber-800">This provider is coming soon. Connection testing and synchronization are unavailable.</p>}
        <div className="mt-6 flex flex-wrap gap-3"><button type="button" disabled={!canTest} onClick={() => void test()} className="rounded-full bg-ink px-5 py-2 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-40">Test connection</button><button type="button" disabled={!canSync} onClick={() => void sync()} className="rounded-full border border-moss/20 px-5 py-2 text-sm font-bold disabled:cursor-not-allowed disabled:opacity-40">Start sync</button><button type="button" disabled={connection.status === "revoked"} onClick={() => void revoke()} className="rounded-full px-5 py-2 text-sm font-bold text-red-700 disabled:opacity-40">Revoke</button></div>
        {message && <p role="status" className="mt-4 text-sm font-bold text-moss/70">{message}</p>}
      </section>
      <div className="grid gap-6 lg:grid-cols-2"><section className="rounded-[2rem] bg-white p-6 shadow-card"><h2 className="text-xl font-black">Sync history</h2><div className="mt-4 divide-y divide-moss/10">{syncs.map((item) => <div key={item.id} className="flex items-center justify-between py-4"><span className="text-sm">{new Date(item.requested_at).toLocaleString()}</span><StatusBadge status={item.status} /></div>)}{!syncs.length && <p className="py-8 text-sm text-moss/50">No sync history.</p>}</div></section><section className="rounded-[2rem] bg-white p-6 shadow-card"><h2 className="text-xl font-black">Recent events</h2><div className="mt-4 divide-y divide-moss/10">{events.map((item) => <div key={item.id} className="py-4"><p className="text-sm font-bold">{item.message}</p><p className="mt-1 text-xs text-moss/50">{new Date(item.created_at).toLocaleString()}</p></div>)}{!events.length && <p className="py-8 text-sm text-moss/50">No events recorded.</p>}</div></section></div>
    </div>
  );
}
