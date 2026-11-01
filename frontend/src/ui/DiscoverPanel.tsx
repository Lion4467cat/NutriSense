import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useExplore } from "../context/explore";
import {
  AREAS,
  BADGES,
  TOTAL_AREAS,
  exploredCount,
  levelFor,
} from "../explore/achievements";
import { ProgressRing } from "./fx";
import { EASE } from "./motion";

/**
 * Field notebook — the payoff surface of the exploration layer. It lists
 * which sections have been opened, which badges have been found and, for
 * the ones still sealed, a riddle rather than the answer. Nothing here
 * scores the nutrition work; it scores curiosity.
 */
export default function DiscoverPanel() {
  const { state, points, panelOpen, setPanelOpen } = useExplore();
  const navigate = useNavigate();
  const reduced = useReducedMotion();
  const closeRef = useRef<HTMLButtonElement>(null);

  const explored = exploredCount(state);
  const level = levelFor(points);
  const ratio = explored / TOTAL_AREAS;
  const found = BADGES.filter((b) => state.badges.includes(b.id));
  const sealed = BADGES.filter((b) => !state.badges.includes(b.id));

  useEffect(() => {
    if (panelOpen) closeRef.current?.focus();
  }, [panelOpen]);

  return (
    <AnimatePresence>
      {panelOpen && (
        <>
          <motion.div
            className="discover-scrim"
            onClick={() => setPanelOpen(false)}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            aria-hidden="true"
          />
          <motion.aside
            className="discover-pop"
            role="dialog"
            aria-labelledby="discover-title"
            initial={{ opacity: 0, y: reduced ? 0 : 22, scale: reduced ? 1 : 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: reduced ? 0 : 14, scale: reduced ? 1 : 0.99 }}
            transition={{ duration: 0.28, ease: EASE }}
          >
            <header className="discover-head">
              <div>
                <span className="discover-kicker">Field notebook</span>
                <h2 id="discover-title">{level.name}</h2>
                <p>
                  {points} {points === 1 ? "point" : "points"}
                  {level.toNext ? ` · ${level.toNext} to the next rank` : " · top rank found"}
                </p>
              </div>
              <button
                ref={closeRef}
                className="icon-btn"
                onClick={() => setPanelOpen(false)}
                aria-label="Close the field notebook"
              >
                ×
              </button>
            </header>

            <div className="discover-progress">
              <ProgressRing
                value={ratio}
                size={44}
                stroke={3}
                label={`${explored} of ${TOTAL_AREAS} sections explored`}
              />
              <div>
                <strong>
                  {explored} of {TOTAL_AREAS} sections
                </strong>
                <span>
                  {explored === TOTAL_AREAS
                    ? "Every room opened. The map is complete."
                    : "Open the sections you have not seen yet."}
                </span>
              </div>
            </div>

            <ul className="discover-areas">
              {AREAS.map((area) => {
                const seen = state.areas.includes(area.id);
                return (
                  <li key={area.id} className={seen ? "seen" : "unseen"}>
                    <button
                      onClick={() => {
                        setPanelOpen(false);
                        navigate(area.to);
                      }}
                    >
                      <span className="discover-tick" aria-hidden="true">
                        {seen ? "✓" : "·"}
                      </span>
                      <span className="discover-area-body">
                        <strong>{area.label}</strong>
                        <small>{seen ? area.hint : "Not opened yet"}</small>
                      </span>
                      <span className="discover-go" aria-hidden="true">
                        ↗
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>

            <div className="discover-badges">
              <h3>
                Badges <span className="num">{found.length}/{BADGES.length}</span>
              </h3>
              {found.length > 0 && (
                <div className="discover-badge-grid">
                  {found.map((badge) => (
                    <motion.article
                      key={badge.id}
                      className="discover-badge found"
                      initial={{ opacity: 0, scale: 0.94 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ duration: 0.3, ease: EASE }}
                    >
                      <span className="badge-pip" aria-hidden="true">
                        ✦
                      </span>
                      <strong>{badge.label}</strong>
                      <small>{badge.note}</small>
                    </motion.article>
                  ))}
                </div>
              )}
              {sealed.length > 0 && (
                <div className="discover-secrets">
                  <span className="discover-secrets-title">Still sealed</span>
                  <ul>
                    {sealed.map((badge) => (
                      <li key={badge.id}>
                        <span className="sealed-glyph" aria-hidden="true">
                          ?
                        </span>
                        {badge.hint}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <footer className="discover-foot">
              Progress is stored on this device only — the same place your meals
              live. Nothing is sent anywhere.
            </footer>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
