"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { authenticate } from "@/lib/api";

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const isLogin = mode === "login";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    const form = new FormData(event.currentTarget);
    try {
      const result = await authenticate(mode, String(form.get("email")), String(form.get("password")));
      localStorage.setItem("access_token", result.access_token);
      router.push("/dashboard");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Authentication failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="w-full max-w-md rounded-[2rem] bg-white p-7 shadow-card sm:p-10">
      <p className="text-xs font-bold uppercase tracking-[.28em] text-moss/50">Gravel Manager</p>
      <h1 className="mt-4 text-4xl font-black tracking-[-.04em]">{isLogin ? "Welcome back" : "Build your engine"}</h1>
      <p className="mt-3 text-sm leading-6 text-moss/60">{isLogin ? "Sign in to see today’s training picture." : "Create your account and start tracking the work."}</p>
      <form onSubmit={submit} className="mt-8 space-y-5">
        <label className="block text-sm font-bold">Email<input required name="email" type="email" autoComplete="email" className="mt-2 w-full rounded-xl border border-moss/15 bg-fog px-4 py-3 outline-none focus:ring-2 focus:ring-gravel" /></label>
        <label className="block text-sm font-bold">Password<input required name="password" type="password" minLength={isLogin ? 1 : 12} autoComplete={isLogin ? "current-password" : "new-password"} className="mt-2 w-full rounded-xl border border-moss/15 bg-fog px-4 py-3 outline-none focus:ring-2 focus:ring-gravel" /></label>
        {error && <p role="alert" className="rounded-xl bg-red-50 px-4 py-3 text-sm font-medium text-red-700">{error}</p>}
        <button disabled={submitting} className="w-full rounded-xl bg-ink px-5 py-4 font-bold text-white transition hover:bg-moss disabled:opacity-50">{submitting ? "Please wait…" : isLogin ? "Sign in" : "Create account"}</button>
      </form>
      <p className="mt-6 text-center text-sm text-moss/60">{isLogin ? "New here?" : "Already training?"} <Link className="font-bold text-ink underline decoration-gravel decoration-2" href={isLogin ? "/register" : "/login"}>{isLogin ? "Create an account" : "Sign in"}</Link></p>
    </div>
  );
}

