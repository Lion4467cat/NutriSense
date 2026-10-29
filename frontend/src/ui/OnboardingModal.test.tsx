import { describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AppProvider } from "../context/AppContext";
import { OnboardingProvider, useOnboarding } from "../context/onboarding";
import { PREFS_KEY, usePrefs } from "../context/prefs";
import { createMemoryStorage } from "../services/storage";
import ModeSwitch from "./ModeSwitch";
import type { ApiClient } from "../services/api";
import type { GoalsResponse, MenuResponse } from "../types/api";

const MENU: MenuResponse = {
  dishes: {},
  days: {},
  bands: {},
  capture_fields: {
    serving_style: { values: ["mixed"] },
    day: { values: ["mon"] },
    band: { values: ["1-5"] },
  },
  remarks: [],
  policy: {
    pass_p: 0.9,
    fail_p: 0.1,
    pass_min: 0.85,
    fail_min: 0.9,
    anchor_prior_cap: 0.6,
    estimated_weight: 0.9,
    base_table_prior: 0.85,
    quality_degraded: 0.9,
    depth_uncalibrated: 0.8,
    lint_min_side_px: 1280,
    policy_version: "current-v9",
  },
};

const GOALS: GoalsResponse = {
  age_bands: ["5-8", "18-29"],
  sexes: ["male", "female"],
  activity_levels: ["low", "moderate", "high"],
  units: { energy: "kcal_per_day", protein: "g_per_day", weight: "kg" },
  daily: {
    "5-8": {
      male: { protein_g: 21.4, energy_kcal: { low: 1450, moderate: 1645, high: 1950 } },
      female: { protein_g: 21.1, energy_kcal: { low: 1335, moderate: 1500, high: 1790 } },
    },
    "18-29": {
      male: { protein_g: 54, energy_kcal: { low: 2400, moderate: 2900, high: 3450 } },
      female: { protein_g: 46, energy_kcal: { low: 1900, moderate: 2300, high: 2650 } },
    },
  },
  source: { s1: "S1", s2: "S2", verified: "2026-10-28" },
  caveats: [],
};

const client: ApiClient = {
  base: "http://test",
  getMenu: () => Promise.resolve(MENU),
  getGoals: () => Promise.resolve(GOALS),
  getHealth: () => Promise.resolve({ status: "ok", phase: "built" }),
  analyze: () => Promise.reject(new Error("not used")),
};

/** Shows what the wizard saved, and can re-open it from anywhere. */
function Harness() {
  const { prefs } = usePrefs();
  const { openWizard } = useOnboarding();
  return (
    <div>
      <output data-testid="name">{prefs.userName}</output>
      <output data-testid="profile">
        {prefs.profile
          ? `${prefs.profile.ageBand}|${prefs.profile.sex}|${prefs.profile.activityLevel}`
          : "none"}
      </output>
      <ModeSwitch />
      <button onClick={openWizard}>reopen</button>
    </div>
  );
}

function renderApp(storage = createMemoryStorage()) {
  render(
    <AppProvider storage={storage} client={client}>
      <OnboardingProvider>
        <Harness />
      </OnboardingProvider>
    </AppProvider>
  );
  return storage;
}

describe("OnboardingWizard", () => {
  it("stays out of School mode and asks on the first switch to General", async () => {
    const user = userEvent.setup();
    const storage = renderApp();

    // School users are never interrupted: the wizard is General-only.
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "General" }));
    expect(await screen.findByText("Set up your profile")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Get started" }));

    const name = await screen.findByLabelText("Display name");
    await user.type(name, "Priya Sharma");

    // Served vocabulary drives the pickers; pick a non-default row.
    await user.click(screen.getByRole("radio", { name: "Female" }));
    await user.selectOptions(screen.getByLabelText("Age band"), "18-29");
    await user.selectOptions(screen.getByLabelText("Activity level"), "high");
    await user.click(screen.getByRole("button", { name: "Continue" }));

    // The preview shows the WHO row for the chosen profile.
    expect(await screen.findByText("2650")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Save & continue" }));
    await user.click(await screen.findByRole("button", { name: "Start analyzing" }));

    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    );
    expect(screen.getByTestId("name")).toHaveTextContent("Priya Sharma");
    expect(screen.getByTestId("profile")).toHaveTextContent("18-29|female|high");

    const stored = JSON.parse(storage.get(PREFS_KEY)!);
    expect(stored.profile).toEqual({
      ageBand: "18-29",
      sex: "female",
      activityLevel: "high",
    });
    // untouched: they accepted the WHO default rather than entering a goal
    expect(stored.goalOverride).toBeNull();
    expect(stored.setupComplete).toBe(true);
  });

  it("does not ask again once a profile is saved", async () => {
    const storage = createMemoryStorage();
    storage.set(
      PREFS_KEY,
      JSON.stringify({
        userName: "Ada",
        profile: { ageBand: "18-29", sex: "female", activityLevel: "moderate" },
        setupComplete: true,
      })
    );
    renderApp(storage);
    expect(screen.getByTestId("name")).toHaveTextContent("Ada");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("skipping invents no profile and asks again on the next General switch", async () => {
    const user = userEvent.setup();
    const storage = renderApp();

    await user.click(screen.getByRole("button", { name: "General" }));
    await user.click(await screen.findByRole("button", { name: "Skip for now" }));
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    );
    expect(JSON.parse(storage.get(PREFS_KEY)!).profile).toBeNull();

    // every switch into General asks again while the profile is missing
    await user.click(screen.getByRole("button", { name: "School" }));
    await user.click(screen.getByRole("button", { name: "General" }));
    expect(await screen.findByText("Set up your profile")).toBeInTheDocument();
  });

  it("can be re-opened from anywhere (Settings → setup guide)", async () => {
    const user = userEvent.setup();
    const storage = createMemoryStorage();
    storage.set(PREFS_KEY, JSON.stringify({}));
    renderApp(storage);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "reopen" }));
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    // editing an existing setup starts on the welcome step, not the form
    expect(screen.getByText("Set up your profile")).toBeInTheDocument();
  });
});
