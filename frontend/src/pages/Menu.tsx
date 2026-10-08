import { Link } from "react-router-dom";
import { useApp } from "../context/AppContext";
import { Card, EmptyState } from "../ui/primitives";
import { IconBook } from "../ui/Icon";

export default function MenuPage() {
  const { menu, menuError, reloadMenu } = useApp();

  if (!menu) {
    return (
      <div className="page">
        <div className="page-head">
          <div>
            <h1 className="page-title">Menu & standards</h1>
            <p className="page-sub">PM POSHAN thresholds and the active menu.</p>
          </div>
        </div>
        <Card>
          <EmptyState
            icon={<IconBook size={20} />}
            title={menuError ? "Menu unavailable" : "Loading menu…"}
            action={
              menuError ? (
                <button className="btn btn-primary" onClick={reloadMenu}>
                  Retry
                </button>
              ) : undefined
            }
          >
            {menuError
              ? "The backend did not return /menu. Check the API connection."
              : "Fetching bands, dishes and capture fields from the backend."}
          </EmptyState>
        </Card>
      </div>
    );
  }

  const bands = Object.entries(menu.bands);
  const dishes = Object.entries(menu.dishes);
  const days = Object.entries(menu.days);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Menu & standards</h1>
          <p className="page-sub">
            PM POSHAN compliance thresholds and the menu NutriSense scores
            against — served live from <span className="mono">GET /menu</span>.
          </p>
        </div>
        <Link className="btn btn-secondary" to="/analyze">
          Analyze meal
        </Link>
      </div>

      <Card
        title="PM POSHAN compliance thresholds"
        sub="Minimum energy and protein per plated mid-day meal, by class band"
      >
        <div className="band-grid">
          {bands.map(([key, b]) => (
            <div className="band-card" key={key}>
              <div className="band-name">Classes {key}</div>
              <div className="band-metric">
                <b>{b.kcal.value}</b>
                <span>kcal minimum</span>
              </div>
              <div className="band-metric">
                <b>{b.protein_g.value}</b>
                <span>g protein minimum</span>
              </div>
            </div>
          ))}
        </div>
        <p className="card-sub" style={{ marginTop: 14 }}>
          Verdict rules (backend-owned): PASS needs P ≥ 0.90 on every mandatory
          nutrient with coverage ≥ 0.85 · FAIL needs P ≤ 0.10 with coverage ≥
          0.90 · anything else is BORDERLINE.
        </p>
      </Card>

      <div style={{ height: 16 }} />

      <Card title={`Dishes (${dishes.length})`} sub="Scored menu items and their scope">
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Dish</th>
                <th>Display name</th>
                <th>Nutrition source</th>
                <th>Status</th>
                <th>Days</th>
              </tr>
            </thead>
            <tbody>
              {dishes.map(([id, d]) => (
                <tr key={id}>
                  <td className="mono">{id}</td>
                  <td className="cell-main">{d.display_name || id}</td>
                  <td>{d.nutrition_source || "—"}</td>
                  <td>
                    {d.status === "out_of_scope" ? (
                      <span className="pill warn">
                        <span className="pill-ico">–</span> OUT OF SCOPE
                      </span>
                    ) : (
                      <span className="pill neutral">scored</span>
                    )}
                  </td>
                  <td>
                    {d.days && d.days.length > 0 ? (
                      <div className="chip-row">
                        {d.days.map((x) => (
                          <span className="tag" key={x}>
                            {x.toUpperCase()}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="muted">any day</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <div style={{ height: 16 }} />

      <div className="dash-grid" style={{ marginBottom: 0 }}>
        <Card title="Weekly rotation" sub="Vegetable focus by day">
          <div className="band-grid">
            {days.map(([key, d]) => (
              <div className="band-card" key={key}>
                <div className="band-name">{key.toUpperCase()}</div>
                <div className="card-sub">{d.note}</div>
                <div className="chip-row" style={{ marginTop: 10 }}>
                  {(d.vegetables || []).slice(0, 6).map((v) => (
                    <span className="tag" key={v}>
                      {v.replace(/_/g, " ")}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Menu remarks" sub="Verbatim from the canteen menu document">
          <ul className="list-clean reason-list">
            {menu.remarks.map((r, i) => (
              <li className="reason-item" key={i}>
                <span className="r-ico info" aria-hidden="true">
                  i
                </span>
                <span>{r}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}
