import { useState } from "react";
import type { ApiClient } from "../services/api";
import type { AnalysisRecord } from "../services/records";
import type { Analysis } from "../types/contract.gen";
import type { MealChatMessage } from "../types/mealCoach";

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : "The meal assistant is unavailable right now.";
}

export default function MealCoach({
  record,
  client,
  updateRecord,
  retryCritique,
}: {
  record: AnalysisRecord;
  client: ApiClient;
  updateRecord: (id: string, update: Partial<AnalysisRecord>) => void;
  retryCritique: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const history = record.chatMessages ?? [];

  const send = async (event: React.FormEvent) => {
    event.preventDefault();
    const question = message.trim();
    if (!question || sending || question.length > 1200) return;
    setSending(true);
    setChatError(null);
    try {
      if (!client.chatAboutMeal) {
        throw new Error("Meal chat is unavailable in this backend client.");
      }
      const reply = await client.chatAboutMeal(
        record.result as Analysis,
        history.slice(-8),
        question,
      );
      const now = new Date().toISOString();
      const next: MealChatMessage[] = [
        ...history,
        { role: "user" as const, content: question, createdAt: now },
        { role: "assistant" as const, content: reply, createdAt: new Date().toISOString() },
      ].slice(-40);
      updateRecord(record.id, { chatMessages: next });
      setMessage("");
    } catch (error) {
      setChatError(messageOf(error));
    } finally {
      setSending(false);
    }
  };

  return (
    <section className="card card-pad meal-coach" aria-labelledby="meal-coach-title">
      <div className="card-head">
        <div>
          <h2 className="card-title" id="meal-coach-title">Meal critique</h2>
          <p className="card-sub">
            Structured meal estimates are sent to Ollama Cloud to generate this critique. The photo and student name are not sent. Some nutrition values may be based on assumptions.
          </p>
        </div>
      </div>

      {record.critiqueStatus === "pending" && (
        <p className="meal-coach-status" role="status">Preparing suggestions for this meal…</p>
      )}
      {record.critiqueStatus === "unavailable" && (
        <div className="banner error" role="status">
          <span>{record.critiqueError || "The meal critique is unavailable right now."}</span>
          <button className="btn btn-secondary btn-sm" onClick={retryCritique}>Retry</button>
        </div>
      )}
      {record.critiqueStatus === "ready" && record.critique && (
        <div className="meal-coach-copy">
          <p>{record.critique.overview}</p>
          <div className="meal-coach-suggestions">
            {!!record.critique.add.length && <div><strong>Consider adding</strong><ul>{record.critique.add.map((item, i) => <li key={`add-${i}`}>{item}</li>)}</ul></div>}
            {!!record.critique.reduce.length && <div><strong>Consider reducing</strong><ul>{record.critique.reduce.map((item, i) => <li key={`reduce-${i}`}>{item}</li>)}</ul></div>}
          </div>
          {record.critique.caveat && <p className="meal-coach-caveat">{record.critique.caveat}</p>}
        </div>
      )}
      {!record.critiqueStatus && (
        <div className="meal-coach-empty">
          <p>No critique was saved for this earlier analysis.</p>
          <button className="btn btn-secondary btn-sm" onClick={retryCritique}>
            Generate critique
          </button>
        </div>
      )}

      <div className="meal-chat">
        <button
          className="btn btn-secondary btn-sm"
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
        >
          {open ? "Close conversation" : "Ask about this meal"}
        </button>
        {!open && record.critiqueStatus === "ready" && record.critique && (
          <div className="meal-chat-prompts" aria-label="Suggested questions">
            <span>Try asking</span>
            {[
              "What is an easy way to add more protein?",
              "What could I swap to make this meal more balanced?",
            ].map((prompt) => (
              <button
                type="button"
                className="meal-chat-prompt"
                key={prompt}
                onClick={() => {
                  setMessage(prompt);
                  setOpen(true);
                }}
              >
                {prompt} <span aria-hidden="true">↗</span>
              </button>
            ))}
          </div>
        )}
        {open && (
          <div className="meal-chat-body">
            {history.map((entry, i) => (
              <div className={`meal-chat-message ${entry.role}`} key={`${entry.createdAt}-${i}`}>
                <strong>{entry.role === "user" ? "You" : "NutriSense"}</strong>
                <p>{entry.content}</p>
              </div>
            ))}
            {chatError && <p className="meal-coach-caveat" role="alert">{chatError}</p>}
            <form onSubmit={send} className="meal-chat-form">
              <label className="sr-only" htmlFor={`meal-chat-${record.id}`}>Ask a question about this meal</label>
              <textarea
                id={`meal-chat-${record.id}`}
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                maxLength={1200}
                rows={2}
                placeholder="Ask about a suggestion or a possible swap…"
              />
              <button className="btn btn-primary btn-sm" disabled={sending || !message.trim()}>
                {sending ? "Thinking…" : "Send"}
              </button>
            </form>
            <small>Conversation is saved with this analysis in this browser.</small>
          </div>
        )}
      </div>
    </section>
  );
}
