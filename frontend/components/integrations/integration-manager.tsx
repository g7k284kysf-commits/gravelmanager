"use client";

import Link from "next/link";
import { ChangeEvent, useEffect, useRef, useState } from "react";
import { StatusBadge } from "@/components/integrations/status-badge";
import {
  createConnection,
  getConnections,
  getImports,
  getProviders,
  getSyncs,
  processImport,
  uploadImport,
  type ImportFile,
  type IntegrationConnection,
  type IntegrationSync,
  type Provider,
} from "@/lib/api";

const allowedExtensions = ["fit", "tcx", "gpx", "csv"];
const maxUploadBytes = 25 * 1024 * 1024;

export function validateUpload(file: File): string | null {
  const extension = file.name.split(".").pop()?.toLowerCase() ?? "";
  if (!allowedExtensions.includes(extension)) return "Choose a FIT, TCX, GPX, or CSV file.";
  if (file.size === 0) return "The selected file is empty.";
  if (file.size > maxUploadBytes) return "The selected file exceeds the 25 MB limit.";
  return null;
}

export function IntegrationManager() {
  const [providers, setProviders] = useState<Provider[] | null>(null);
  const [connections, setConnections] = useState<IntegrationConnection[]>([]);
  const [imports, setImports] = useState<ImportFile[]>([]);
  const [syncs, setSyncs] = useState<IntegrationSync[]>([]);
  const [error, setError] = useState("");
  const [uploadState, setUploadState] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  async function load() {
    setError("");
    try {
      const [providerData, connectionData, importData, syncData] = await Promise.all([
        getProviders(), getConnections(), getImports(), getSyncs(),
      ]);
      setProviders(providerData);
      setConnections(connectionData);
      setImports(importData);
      setSyncs(syncData);
    } catch {
      setError("We could not load your integrations. Check your connection and try again.");
    }
  }

  useEffect(() => { void load(); }, []);

  async function connectManualUpload() {
    try {
      const connection = await createConnection("manual_upload");
      setConnections((current) => [connection, ...current]);
    } catch {
      setError("Manual upload could not be enabled.");
    }
  }

  async function selectedFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    const validation = validateUpload(file);
    if (validation) {
      setUploadState(validation);
      return;
    }
    setUploadState("Uploading…");
    try {
      const uploaded = await uploadImport(file);
      setUploadState("Processing…");
      await processImport(uploaded.id);
      const history = await getImports();
      setImports(history);
      setUploadState("Import finished. Review the result below.");
    } catch {
      setUploadState("Upload or processing failed. The file was not imported.");
    } finally {
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  if (error && providers === null) {
    return (
      <div role="alert" className="rounded-[2rem] bg-white p-8 shadow-card">
        <p className="font-bold text-red-800">{error}</p>
        <button type="button" onClick={() => void load()} className="mt-4 rounded-full bg-ink px-5 py-2 text-sm font-bold text-white">Try again</button>
      </div>
    );
  }

  if (providers === null) {
    return <div role="status" aria-label="Loading integrations" className="h-64 animate-pulse rounded-[2rem] bg-white/70" />;
  }

  return (
    <div className="space-y-10">
      {error && <p role="alert" className="rounded-2xl bg-red-50 p-4 text-red-800">{error}</p>}
      <section aria-labelledby="providers-heading">
        <h2 id="providers-heading" className="text-2xl font-black">Providers</h2>
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          {providers.map((provider) => {
            const connection = connections.find((item) => item.provider_key === provider.provider_key);
            return (
              <article key={provider.provider_key} className="rounded-[2rem] bg-white p-6 shadow-card">
                <div className="flex items-start justify-between gap-4">
                  <div><h3 className="text-xl font-black">{provider.display_name}</h3><p className="mt-2 text-sm leading-6 text-moss/60">{provider.description}</p></div>
                  <StatusBadge status={connection?.status ?? (provider.availability === "coming_soon" ? "coming soon" : "manual import only")} />
                </div>
                <p className="mt-5 text-xs font-bold uppercase tracking-wider text-moss/50">{provider.capabilities.map((item) => item.replaceAll("_", " ")).join(" · ")}</p>
                <div className="mt-5">
                  {connection ? <Link href={`/settings/integrations/${connection.id}`} className="font-bold underline decoration-gravel decoration-2">Manage connection</Link> : provider.provider_key === "manual_upload" ? <button type="button" onClick={() => void connectManualUpload()} className="rounded-full bg-ink px-5 py-2 text-sm font-bold text-white">Enable manual upload</button> : <span className="text-sm font-bold text-moss/40">Coming soon</span>}
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <section aria-labelledby="upload-heading" className="rounded-[2rem] bg-ink p-6 text-white shadow-card sm:p-8">
        <p className="text-xs font-bold uppercase tracking-[.2em] text-gravel">Manual import</p>
        <h2 id="upload-heading" className="mt-2 text-2xl font-black">Bring your training files</h2>
        <p className="mt-2 max-w-xl text-sm leading-6 text-white/60">FIT, TCX, GPX and generic CSV files up to 25 MB. Duplicate files are detected by checksum.</p>
        <label className="mt-6 block cursor-pointer rounded-2xl border border-dashed border-white/30 p-6 text-center font-bold hover:border-gravel focus-within:ring-2 focus-within:ring-gravel">
          Choose a file
          <input ref={inputRef} type="file" accept=".fit,.tcx,.gpx,.csv" onChange={(event) => void selectedFile(event)} className="sr-only" aria-label="Upload training file" />
        </label>
        {uploadState && <p role="status" className="mt-4 text-sm text-gravel">{uploadState}</p>}
      </section>

      <History imports={imports} syncs={syncs} />
    </div>
  );
}

function History({ imports, syncs }: { imports: ImportFile[]; syncs: IntegrationSync[] }) {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <section className="rounded-[2rem] bg-white p-6 shadow-card" aria-labelledby="imports-heading">
        <h2 id="imports-heading" className="text-xl font-black">Import history</h2>
        <div className="mt-5 divide-y divide-moss/10">
          {imports.map((item) => <div key={item.id} className="flex items-center justify-between gap-4 py-4"><div className="min-w-0"><p className="truncate font-bold">{item.original_filename}</p><p className="text-xs text-moss/50">{new Date(item.uploaded_at).toLocaleString()}</p>{typeof item.metadata.records_created === "number" && <p className="text-xs text-moss/50">{item.metadata.records_created} created · {item.metadata.records_updated ?? 0} updated · {item.metadata.records_skipped ?? 0} skipped · {item.metadata.records_failed ?? 0} failed</p>}</div><StatusBadge status={item.status} /></div>)}
          {!imports.length && <p className="py-8 text-sm text-moss/50">No files imported yet.</p>}
        </div>
      </section>
      <section className="rounded-[2rem] bg-white p-6 shadow-card" aria-labelledby="sync-heading">
        <h2 id="sync-heading" className="text-xl font-black">Sync history</h2>
        <div className="mt-5 divide-y divide-moss/10">
          {syncs.map((sync) => <div key={sync.id} className="flex items-center justify-between gap-4 py-4"><div><p className="font-bold">{sync.provider_key}</p><p className="text-xs text-moss/50">{sync.records_created} created · {sync.records_skipped} skipped · {sync.records_failed} failed</p></div><StatusBadge status={sync.status} /></div>)}
          {!syncs.length && <p className="py-8 text-sm text-moss/50">No synchronizations have run yet.</p>}
        </div>
      </section>
    </div>
  );
}
