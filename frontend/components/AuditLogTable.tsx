"use client";
import type { AuditEvent } from "@/lib/types";

function fmt(iso: string): string {
  const hasTZ = /Z$|[+-]\d{2}:?\d{2}$/.test(iso);
  return new Date(hasTZ ? iso : iso + "Z").toLocaleString();
}

export function AuditLogTable({ events }: { events: AuditEvent[] }) {
  if (events.length === 0) return <p className="text-slate-500">No events yet.</p>;
  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-left text-slate-600">
          <tr>
            <th className="px-3 py-2">When</th>
            <th className="px-3 py-2">Actor</th>
            <th className="px-3 py-2">Event</th>
            <th className="px-3 py-2">Subject</th>
            <th className="px-3 py-2">Change</th>
          </tr>
        </thead>
        <tbody>
          {events.map((e) => (
            <tr key={e.id} className="border-t border-slate-100">
              <td className="px-3 py-2 text-slate-600">{fmt(e.created_at)}</td>
              <td className="px-3 py-2 font-mono text-xs">{e.actor}</td>
              <td className="px-3 py-2">{e.event_type}</td>
              <td className="px-3 py-2 text-slate-600">
                {e.subject_kind} <span className="font-mono">#{e.subject_id}</span>
              </td>
              <td className="px-3 py-2 font-mono text-xs text-slate-500">
                {e.before ? (<>
                  <span className="text-red-600">{JSON.stringify(e.before)}</span>{" → "}
                </>) : null}
                {e.after ? (<span className="text-emerald-600">{JSON.stringify(e.after)}</span>) : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
