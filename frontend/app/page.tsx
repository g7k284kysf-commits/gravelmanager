import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-ink text-white">
      <nav className="mx-auto flex max-w-7xl items-center justify-between px-6 py-6">
        <span className="text-lg font-black tracking-tight">GRAVEL<span className="text-gravel">/</span>MANAGER</span>
        <Link href="/login" className="rounded-full border border-white/20 px-5 py-2 text-sm font-semibold hover:border-gravel">Sign in</Link>
      </nav>
      <section className="mx-auto grid max-w-7xl gap-12 px-6 pb-20 pt-16 lg:grid-cols-[1.2fr_.8fr] lg:pt-28">
        <div>
          <p className="mb-6 text-sm font-bold uppercase tracking-[.3em] text-gravel">Performance, distilled</p>
          <h1 className="max-w-4xl text-6xl font-black leading-[.92] tracking-[-.06em] sm:text-8xl">Ride farther.<br />Train smarter.</h1>
          <p className="mt-8 max-w-xl text-lg leading-8 text-white/60">One clean view of your fitness, fatigue, form, and every hard-earned kilometre.</p>
          <div className="mt-10 flex flex-wrap gap-4">
            <Link href="/register" className="rounded-full bg-gravel px-7 py-4 font-bold text-ink">Start training</Link>
            <Link href="/dashboard" className="rounded-full border border-white/20 px-7 py-4 font-bold">View dashboard</Link>
          </div>
        </div>
        <div className="relative min-h-80 overflow-hidden rounded-[2rem] bg-moss p-8 shadow-2xl">
          <div className="absolute -right-20 -top-20 h-72 w-72 rounded-full border-[42px] border-gravel/20" />
          <p className="text-sm text-white/50">TODAY&apos;S FORM</p>
          <p className="mt-4 text-8xl font-black text-gravel">+7</p>
          <div className="absolute bottom-8 left-8 right-8 grid grid-cols-2 gap-4">
            <div className="rounded-2xl bg-white/10 p-4"><span className="text-xs text-white/50">CTL</span><p className="text-3xl font-bold">68.4</p></div>
            <div className="rounded-2xl bg-white/10 p-4"><span className="text-xs text-white/50">THIS WEEK</span><p className="text-3xl font-bold">7.8h</p></div>
          </div>
        </div>
      </section>
    </main>
  );
}
