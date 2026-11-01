import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useMenu } from "../context/menu";
import { usePrefs } from "../context/prefs";
import { useRecords } from "../context/records";
import { VerdictPill } from "../result/VerdictPill";
import { Card, EmptyState } from "../ui/primitives";
import { Magnetic, TiltPanel } from "../ui/fx";
import { IconCamera, IconHistory } from "../ui/Icon";
import { revealContainer, revealItem, scrollReveal } from "../ui/motion";
import { formatDate, formatNum } from "../utils/format";

const STEPS = [
  {
    n: "01",
    title: "Place the card",
    body: "Lay the 60 mm reference card next to the plate. It gives the camera a real-world scale, so grams come from geometry, not guesswork.",
  },
  {
    n: "02",
    title: "Snap the meal",
    body: "One top-down photo. Segmentation finds the dish, the classifier names it, and depth imaging turns plate area into portion weight.",
  },
  {
    n: "03",
    title: "Read the result",
    body: "Dish, grams and every mandatory nutrient, checked against the standard — with an honest interval and a plain-language verdict.",
  },
];

export default function DashboardPage() {
  const { records } = useRecords();
  const { apiUp } = useMenu();
  const { prefs } = usePrefs();
  const navigate = useNavigate();
  const general = (prefs.mode ?? "school") === "general";

  return (
    <div className="page page-dashboard">
      <motion.header
        className="home-hero"
        variants={revealContainer}
        initial="hidden"
        animate="show"
      >
        <motion.span className="eyebrow" variants={revealItem}>
          NutriSense <i /> {general ? "Meal journal" : "School meals"}
        </motion.span>
        <motion.h1 className="page-title" variants={revealItem}>
          Know what's on the plate, <em>in seconds.</em>
        </motion.h1>
        <motion.p className="page-sub" variants={revealItem}>
          NutriSense reads a single meal photo — dish, portion, nutrients —
          and checks it against{" "}
          {general ? "your daily goal" : "the PM POSHAN standard"}. No kitchen
          scale, no manual entry, no guessing.
        </motion.p>
        <motion.div className="home-cta" variants={revealItem}>
          <Magnetic strength={6}>
            <button className="btn btn-primary btn-lg" onClick={() => navigate("/analyze")}>
              <IconCamera size={16} /> Analyze a meal
            </button>
          </Magnetic>
          {records.length > 0 && (
            <Link className="btn btn-ghost btn-lg" to="/history">
              <IconHistory size={16} /> View history
            </Link>
          )}
        </motion.div>
      </motion.header>

      {apiUp === false && (
        <div className="home-service-note" role="status">
          <span aria-hidden="true" /> New analyses are paused while the service
          is offline. Your saved meals are still available.
        </div>
      )}

      <motion.section
        className="home-how"
        aria-label="How it works"
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, margin: "-60px" }}
      >
        <motion.h2 className="home-how-title" variants={scrollReveal}>
          How it works
        </motion.h2>
        <div className="home-steps">
          {STEPS.map((step) => (
            <motion.article
              className="home-step"
              key={step.n}
              variants={scrollReveal}
            >
              <span className="home-step-n num">{step.n}</span>
              <h3>{step.title}</h3>
              <p>{step.body}</p>
            </motion.article>
          ))}
        </div>
      </motion.section>

      <motion.div
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, margin: "-40px" }}
        variants={scrollReveal}
      >
        <TiltPanel className="tilt-card" max={2.5}>
        <Card
          className="home-meals-card"
          title="Recent meals"
          sub={`${records.length} saved ${records.length === 1 ? "meal" : "meals"} on this device`}
          action={
            records.length > 0 ? (
              <Link className="btn btn-ghost btn-sm" to="/history">
                View history <span aria-hidden="true">↗</span>
              </Link>
            ) : undefined
          }
        >
          {records.length === 0 ? (
            <EmptyState
              icon={<IconCamera size={20} />}
              title="Your meal journal starts here"
            >
              Add a meal photo to get an estimate and practical ideas for what
              to add or ease back on.
            </EmptyState>
          ) : (
            <div className="home-meal-list">
              {records.slice(0, 5).map((record) => (
                <Link
                  className="home-meal-row"
                  key={record.id}
                  to={`/result/${record.id}`}
                >
                  {record.photo ? (
                    <img src={record.photo} alt="" />
                  ) : (
                    <span className="home-meal-placeholder" aria-hidden="true">
                      <IconCamera size={18} />
                    </span>
                  )}
                  <span className="home-meal-main">
                    <strong>{record.summary.dish || "Unrecognized meal"}</strong>
                    <small>
                      {formatDate(record.createdAt)}
                      {record.student?.name ? ` · ${record.student.name}` : ""}
                    </small>
                  </span>
                  <span className="home-meal-result">
                    {general ? (
                      <>
                        <strong>
                          {record.summary.kcal == null
                            ? "—"
                            : `${formatNum(record.summary.kcal, 0)} kcal`}
                        </strong>
                        <small>
                          {record.summary.protein == null
                            ? "Nutrition estimate"
                            : `${formatNum(record.summary.protein, 1)} g protein`}
                        </small>
                      </>
                    ) : (
                      <VerdictPill verdict={record.summary.verdict} />
                    )}
                  </span>
                  <span className="home-meal-arrow" aria-hidden="true">
                    ↗
                  </span>
                </Link>
              ))}
            </div>
          )}
        </Card>
        </TiltPanel>
      </motion.div>
    </div>
  );
}
