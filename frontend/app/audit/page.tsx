"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { AuditEvent } from "@/lib/types";
import { AuditLogTable } from "@/components/AuditLogTable";
import { Breadcrumbs } from "@/components/Breadcrumbs";

export default function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[] | null>(null);
  useEffect(() => { api.listAuditEvents().then(setEvents); }, []);
  return (
    <main className="space-y-6">
      <Breadcrumbs items={[{ label: "Home", href: "/" }, { label: "Audit log" }]} />

      <Link href="/" className="text-sm text-slate-600 hover:underline">← Home</Link>
      <header>
        <h1 className="text-2xl font-bold">Audit log</h1>
        <p className="text-slate-600">
          Every analysis run and finding update. Immutable, append-only.
        </p>
      </header>
      {events === null ? <p>Loading…</p> : <AuditLogTable events={events} />}
    </main>
  );
}
