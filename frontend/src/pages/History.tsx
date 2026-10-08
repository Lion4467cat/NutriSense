import { useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useApp } from "../context/AppContext";
import { Card, EmptyState, VerdictPill } from "../ui/primitives";
import { IconHistory, IconSearch, IconTrash } from "../ui/Icon";
import { formatDate, formatNum, formatPct } from "../utils/format";

type SortKey = "date" | "dish" | "verdict" | "coverage";

export default function HistoryPage() {
  const { records, removeRecord } = useApp();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [verdict, setVerdict] = useState("");
  const [sort, setSort] = useState<SortKey>("date");
  const q = params.get("q") || "";

  const setQ = (v: string) => {
    const next = new URLSearchParams(params);
    if (v) next.set("q", v);
    else next.delete("q");
    setParams(next, { replace: true });
  };

  const filtered = useMemo(() => {
    let out = records;
    if (q.trim()) {
      const needle = q.trim().toLowerCase();
      out = out.filter((r) =>
        [r.summary.dish, r.student?.name, r.day, r.band, r.summary.verdict]
          .filter(Boolean)
          .some((x) => String(x).toLowerCase().includes(needle))
      );
    }
    if (verdict) out = out.filter((r) => r.summary.verdict === verdict);
    const dir = sort === "date" ? -1 : 1;
    out = [...out].sort((a, b) => {
      if (sort === "date") return dir * (Date.parse(a.createdAt) - Date.parse(b.createdAt));
      if (sort === "dish")
        return dir * (a.summary.dish || "").localeCompare(b.summary.dish || "");
      if (sort === "coverage")
        return dir * ((a.summary.coverage ?? -1) - (b.summary.coverage ?? -1));
      return dir * a.summary.verdict.localeCompare(b.summary.verdict);
    });
    return out;
  }, [records, q, verdict, sort]);

  const toggleSort = (key: SortKey) => setSort(key);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Analysis history</h1>
          <p className="page-sub">
            Every capture you have analyzed, with verdict, nutrition and
            coverage.
          </p>
        </div>
        <span className="local-note">
          <span className="dot up" aria-hidden="true" /> Stored locally in this
          browser — {records.length} record{records.length === 1 ? "" : "s"}
        </span>
      </div>

      <div className="filter-bar">
        <span className="search-box" style={{ width: 260 }}>
          <IconSearch size={14} />
          <input
            type="search"
            placeholder="Search dish, student, day…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            aria-label="Search analyses"
          />
        </span>

        <select
          className="select"
          value={verdict}
          onChange={(e) => setVerdict(e.target.value)}
          aria-label="Filter by verdict"
        >
          <option value="">All verdicts</option>
          <option value="PASS">PASS</option>
          <option value="BORDERLINE">BORDERLINE</option>
          <option value="FAIL">FAIL</option>
          <option value="cannot_verify">CANNOT VERIFY</option>
          <option value="out_of_scope">OUT OF SCOPE</option>
        </select>

        <select
          className="select"
          value={sort}
          onChange={(e) => setSort(e.target.value as SortKey)}
          aria-label="Sort"
        >
          <option value="date">Newest first</option>
          <option value="dish">Dish A–Z</option>
          <option value="coverage">Coverage</option>
          <option value="verdict">Verdict</option>
        </select>

        {(q || verdict) && (
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => {
              setQ("");
              setVerdict("");
            }}
          >
            Clear filters
          </button>
        )}
      </div>

      {records.length === 0 ? (
        <Card>
          <EmptyState
            icon={<IconHistory size={20} />}
            title="No analyses"
            action={
              <button className="btn btn-primary" onClick={() => navigate("/analyze")}>
                Analyze your first meal
              </button>
            }
          >
            Your meal analyses will appear here.
          </EmptyState>
        </Card>
      ) : filtered.length === 0 ? (
        <Card>
          <EmptyState icon={<IconSearch size={20} />} title="No results">
            No meals match your filters.
          </EmptyState>
        </Card>
      ) : (
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>
                  <button className="sort-btn" onClick={() => toggleSort("date")}>
                    Date {sort === "date" ? "↓" : ""}
                  </button>
                </th>
                <th>
                  <button className="sort-btn" onClick={() => toggleSort("dish")}>
                    Dish {sort === "dish" ? "↓" : ""}
                  </button>
                </th>
                <th>Student</th>
                <th>Portion</th>
                <th>Energy</th>
                <th>Protein</th>
                <th>
                  <button className="sort-btn" onClick={() => toggleSort("coverage")}>
                    Coverage {sort === "coverage" ? "↓" : ""}
                  </button>
                </th>
                <th>Verdict</th>
                <th aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => (
                <tr
                  key={r.id}
                  className="clickable"
                  onClick={() => navigate(`/result/${r.id}`)}
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") navigate(`/result/${r.id}`);
                  }}
                >
                  <td>
                    <div className="cell-main">{formatDate(r.createdAt)}</div>
                    <div className="cell-sub">
                      {r.day.toUpperCase()} · band {r.band}
                    </div>
                  </td>
                  <td className="cell-main">{r.summary.dish || "—"}</td>
                  <td>{r.student?.name || <span className="muted">—</span>}</td>
                  <td className="num">
                    {r.summary.grams != null ? `${formatNum(r.summary.grams, 0)} g` : "—"}
                  </td>
                  <td className="num">
                    {r.summary.kcal != null ? `${formatNum(r.summary.kcal, 0)} kcal` : "—"}
                  </td>
                  <td className="num">
                    {r.summary.protein != null ? `${formatNum(r.summary.protein, 1)} g` : "—"}
                  </td>
                  <td className="num">
                    {r.summary.coverage != null ? formatPct(r.summary.coverage, 0) : "—"}
                  </td>
                  <td>
                    <VerdictPill verdict={r.summary.verdict} />
                  </td>
                  <td onClick={(e) => e.stopPropagation()}>
                    <button
                      className="icon-btn"
                      aria-label={`Delete analysis from ${formatDate(r.createdAt)}`}
                      title="Delete record"
                      onClick={() => removeRecord(r.id)}
                    >
                      <IconTrash size={15} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
