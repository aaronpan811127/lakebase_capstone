import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { apiGet, apiPost } from "@/api/client";
import type { ConfigOut, GenieMessageOut } from "@/api/types";

interface ChatMsg {
  role: "user" | "bot";
  text: string;
  sql?: string | null;
  columns?: string[] | null;
  rows?: unknown[][] | null;
}

const TERMINAL = new Set(["COMPLETED", "FAILED", "CANCELLED", "QUERY_RESULT_EXPIRED"]);
const POLL_MS = 1200;
const MAX_POLLS = 25; // ~30s cap

export default function GenieWidget() {
  const [open, setOpen] = useState(false);
  const [enlarged, setEnlarged] = useState(false);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const conversationId = useRef<string | null>(null);
  const bodyRef = useRef<HTMLDivElement>(null);

  const { data: config } = useQuery({
    queryKey: ["config"],
    queryFn: () => apiGet<ConfigOut>("/api/config"),
    staleTime: 5 * 60_000,
    enabled: open,
  });

  useEffect(() => {
    bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

  async function pollMessage(convId: string, msgId: string): Promise<GenieMessageOut> {
    for (let i = 0; i < MAX_POLLS; i++) {
      const m = await apiGet<GenieMessageOut>(
        `/api/genie/conversations/${convId}/messages/${msgId}`
      );
      if (m.status && TERMINAL.has(m.status)) return m;
      await sleep(POLL_MS);
    }
    throw new Error("Genie is taking too long — try again.");
  }

  async function send() {
    const q = input.trim();
    if (!q || busy) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: q }]);
    setBusy(true);
    try {
      let convId = conversationId.current;
      let msgId: string;
      if (!convId) {
        const started = await apiPost<GenieMessageOut>("/api/genie/conversations", { content: q });
        convId = started.conversation_id;
        conversationId.current = convId;
        msgId = started.message_id;
      } else {
        const sent = await apiPost<GenieMessageOut>(
          `/api/genie/conversations/${convId}/messages`,
          { content: q }
        );
        msgId = sent.message_id;
      }
      const final = await pollMessage(convId, msgId);
      const text =
        final.answer_text ||
        final.content ||
        (final.status === "FAILED" ? "Genie couldn't answer that." : "(no answer)");
      setMessages((m) => [
        ...m,
        { role: "bot", text, sql: final.query, columns: final.result_columns, rows: final.result_rows },
      ]);
    } catch (e) {
      setMessages((m) => [...m, { role: "bot", text: (e as Error).message }]);
    } finally {
      setBusy(false);
    }
  }

  const spaceUrl =
    config && `${config.databricks_host}/genie/rooms/${config.genie_space_id}`;

  if (!open) {
    return (
      <button className="genie-fab" onClick={() => setOpen(true)} title="Ask Genie" aria-label="Ask Genie">
        ✦
      </button>
    );
  }

  return (
    <div className={"genie-panel" + (enlarged ? " enlarged" : "")}>
      <div className="genie-header">
        <span className="title">✦ Ask Genie</span>
        {enlarged && spaceUrl && (
          <a href={spaceUrl} target="_blank" rel="noreferrer" className="back-link">Open in workspace ↗</a>
        )}
        <button onClick={() => setEnlarged((e) => !e)} title="Toggle size">
          {enlarged ? "⤡" : "⤢"}
        </button>
        <button onClick={() => setOpen(false)} title="Close">✕</button>
      </div>

      <div className="genie-body" ref={bodyRef}>
        {messages.length === 0 && !busy && (
          <div className="genie-empty">
            Ask about your customers.<br />
            e.g. "Top 5 segments by LTV last quarter"
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`genie-msg ${m.role}`}>
            <div>{m.text}</div>
            {m.sql && <div className="sql">{m.sql}</div>}
            {m.columns && m.rows && m.rows.length > 0 && (
              <div className="genie-result">
                <table>
                  <thead>
                    <tr>{m.columns.map((c) => <th key={c}>{c}</th>)}</tr>
                  </thead>
                  <tbody>
                    {m.rows.slice(0, 10).map((row, ri) => (
                      <tr key={ri}>
                        {(row as unknown[]).map((cell, ci) => <td key={ci}>{String(cell)}</td>)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ))}
        {busy && (
          <div className="genie-msg bot">
            <span className="typing"><span /><span /><span /></span>
          </div>
        )}
      </div>

      <div className="genie-input">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Ask a question…"
          disabled={busy}
        />
        <button className="primary" onClick={send} disabled={busy || !input.trim()}>Send</button>
      </div>
    </div>
  );
}
