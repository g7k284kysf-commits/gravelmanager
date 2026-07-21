import Link from "next/link";
import { ConnectionDetail } from "@/components/integrations/connection-detail";

export default async function ConnectionPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <main className="min-h-screen bg-fog"><header className="bg-ink text-white"><div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5"><Link href="/dashboard" className="font-black">GRAVEL<span className="text-gravel">/</span>MANAGER</Link><Link href="/settings/integrations" className="text-sm font-bold text-white/70">All integrations</Link></div></header><div className="mx-auto max-w-5xl px-5 py-10"><ConnectionDetail connectionId={Number(id)} /></div></main>
  );
}
