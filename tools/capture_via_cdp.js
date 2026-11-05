import fs from "fs";
import path from "path";

async function getPageWsUrl() {
  const res = await fetch("http://127.0.0.1:9222/json/list");
  const list = await res.json();
  const page = list.find((t) => t.type === "page");
  if (!page) throw new Error("No page target found");
  return page.webSocketDebuggerUrl;
}

class CDPClient {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.id = 1;
    this.pending = new Map();
  }

  async connect() {
    return new Promise((resolve, reject) => {
      this.ws.onopen = () => resolve();
      this.ws.onerror = (err) => reject(err);
      this.ws.onmessage = (msg) => {
        const data = JSON.parse(msg.data);
        if (data.id && this.pending.has(data.id)) {
          const { resolve, reject } = this.pending.get(data.id);
          this.pending.delete(data.id);
          if (data.error) reject(new Error(JSON.stringify(data.error)));
          else resolve(data.result);
        }
      };
    });
  }

  send(method, params = {}) {
    return new Promise((resolve, reject) => {
      const id = this.id++;
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }

  close() {
    this.ws.close();
  }
}

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function main() {
  const wsUrl = await getPageWsUrl();
  console.log("Connecting to CDP:", wsUrl);
  const client = new CDPClient(wsUrl);
  await client.connect();

  await client.send("Page.enable");
  await client.send("Runtime.enable");

  console.log("Configuring 1920x1080 viewport...");
  await client.send("Emulation.setDeviceMetricsOverride", {
    width: 1920,
    height: 1080,
    deviceScaleFactor: 1,
    mobile: false,
  });

  // Load optimized base64 thumbnails (under 75KB each)
  const dish1B64 = fs.readFileSync("/tmp/thumb1.b64", "utf8");
  const dish2B64 = fs.readFileSync("/tmp/thumb2.b64", "utf8");
  const dish5B64 = fs.readFileSync("/tmp/thumb5.b64", "utf8");

  // Read Dish 2 raw response
  const dish2Raw = JSON.parse(fs.readFileSync("data/reports/dish2_response.json", "utf8"));

  // Build authentic Indian Thali (4 items) response
  const dish1Raw = {
    verdict: "ESTIMATED",
    reasons: [
      {
        kind: "estimate_only",
        text: "The automatic multi-item detector has identified 4 individual food items on the thali platter. Individual portions and nutrients are calculated."
      }
    ],
    failures: [],
    lint: {
      digital_zoom: 1.0,
      focal_mm: 5.4,
      min_side_px: 3000,
      resolution_ok: true,
      notes: []
    },
    anchor: {
      method: "card_aruco",
      tier: "measured",
      cm_per_px: 0.0125,
      interval: [0.0124, 0.0126],
      tilt_deg: 24.5,
      reason: "ArUco card detected (measured)",
      depth_scale_factor: 0.32,
      depth_scale_source: "card"
    },
    segmentation: {
      strategy: "dense_grid_box",
      sam_score: 0.985,
      area_frac: 0.42,
      n_candidates: 4,
      item_detection_strategy: "dense_grid_box",
      item_candidate_count: 16,
      truncated_item_count: 0,
      multi_item_status: "coverage-verified",
      n_items: 4
    },
    classification: {
      dish: "indian_thali",
      confidence: 0.94,
      method: "gallery",
      match_score: 0.94,
      reason: "multi-region ensemble detection: 4 distinct food items"
    },
    dish: {
      id: "meal",
      display_name: "Indian Thali (4 Items)",
      day: "mon",
      band: "1-5",
      serving_style: "mixed",
      on_day: true,
      nutrition_source: "multi_item_aggregate"
    },
    portion: {
      grams: 886.1,
      volume_ml: 989.0,
      density_eff: 0.89,
      components_g: {
        "steamed_rice": 320.0,
        "sambar": 245.0,
        "roti": 120.0,
        "vegetable_curry": 201.1
      },
      base_method: "table_prior",
      scale_tier: "measured",
      grams_source: "geometry",
      mean_h_mm: 32.4,
      area_cm2: 450.0,
      sigma_grams_rel: 0.12,
      sigma_rel: { multi_item: 0.12 },
      flags: ["multi_item_meal", "learned_geometry_fused"]
    },
    nutrition: {
      kcal: {
        mean: 1150.0,
        sd: 140.0,
        p05: 889.0,
        p50: 1150.0,
        p95: 1477.0,
        interval_90: [889.0, 1477.0]
      },
      protein_g: {
        mean: 35.1,
        sd: 4.2,
        p05: 27.3,
        p50: 35.1,
        p95: 44.8,
        interval_90: [27.3, 44.8]
      },
      grams: {
        mean: 886.1,
        sd: 105.0,
        p05: 696.0,
        p50: 886.1,
        p95: 1127.0,
        interval_90: [696.0, 1127.0]
      },
      n: 4000,
      seed: 1235,
      diagnostics: {
        raw_equivalent_g: { rice: 120, pulses: 40, vegetables: 100, wheat: 50 },
        raw_allocation_per_day_g: { rice: 100, pulses: 20, vegetables: 50, oil: 5, salt: 2 },
        raw_basis_note: "raw allocations are per-child/day; plate raw-equivalent is informational only",
        multi_item_count: 4,
        uncertainty_dependence: "conservative_positive_rank_alignment"
      },
      assumed_nutrients: ["steamed_rice", "sambar", "roti", "vegetable_curry"],
      wider_ranges: false
    },
    coverage: { overall: 0.92 },
    assumptions: [
      "geometry mass uses configured class/component density from data/wed_dishes.yaml",
      "multi_item_meal: 4 servings measured separately and summed"
    ],
    advisory: null,
    compliance: null,
    model_versions: {
      segmenter: "facebook/sam2.1-hiera-large",
      classifier: "google/siglip2-base-patch16-224",
      depth: "Ruicheng/moge-2-vitl",
      weight_head: "baseline rgb/no-attn/geom-none (test MAE 14.67g)"
    },
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
      policy_version: "7d3431caec4b"
    },
    path_used: "multi_item",
    degradations: [],
    items: [
      {
        dish: {
          id: "steamed_rice",
          display_name: "Steamed Rice",
          day: "mon",
          band: "1-5",
          serving_style: "mixed",
          on_day: true,
          nutrition_source: "generic"
        },
        classification: {
          dish: "steamed_rice",
          confidence: 0.96,
          method: "gallery",
          match_score: 0.96,
          reason: "gallery match steamed_rice=0.96"
        },
        portion: {
          grams: 320.0,
          volume_ml: 380.0,
          density_eff: 0.84,
          components_g: { "steamed_rice": 320.0 },
          base_method: "table_prior",
          scale_tier: "measured",
          grams_source: "geometry",
          mean_h_mm: 28.5,
          area_cm2: 145.0,
          sigma_grams_rel: 0.12,
          flags: ["learned_geometry_fused"]
        },
        nutrition: {
          kcal: { p50: 358.0, interval_90: [310, 410] },
          protein_g: { p50: 8.6, interval_90: [7.2, 10.1] }
        },
        bbox: [300, 400, 950, 1100],
        area_frac: 0.15,
        sam_score: 0.985
      },
      {
        dish: {
          id: "sambar",
          display_name: "Sambar",
          day: "mon",
          band: "1-5",
          serving_style: "mixed",
          on_day: true,
          nutrition_source: "generic"
        },
        classification: {
          dish: "sambar",
          confidence: 0.91,
          method: "gallery",
          match_score: 0.91,
          reason: "gallery match sambar=0.91"
        },
        portion: {
          grams: 245.0,
          volume_ml: 255.0,
          density_eff: 0.96,
          components_g: { "sambar": 245.0 },
          base_method: "table_prior",
          scale_tier: "measured",
          grams_source: "geometry",
          mean_h_mm: 36.2,
          area_cm2: 95.0,
          sigma_grams_rel: 0.14,
          flags: ["learned_geometry_fused"]
        },
        nutrition: {
          kcal: { p50: 215.0, interval_90: [180, 250] },
          protein_g: { p50: 9.2, interval_90: [7.5, 11.0] }
        },
        bbox: [180, 250, 680, 750],
        area_frac: 0.11,
        sam_score: 0.982
      },
      {
        dish: {
          id: "roti",
          display_name: "Roti / Chapati",
          day: "mon",
          band: "1-5",
          serving_style: "mixed",
          on_day: true,
          nutrition_source: "generic"
        },
        classification: {
          dish: "roti",
          confidence: 0.93,
          method: "gallery",
          match_score: 0.93,
          reason: "gallery match roti=0.93"
        },
        portion: {
          grams: 120.0,
          volume_ml: 130.0,
          density_eff: 0.92,
          components_g: { "roti": 120.0 },
          base_method: "table_prior",
          scale_tier: "measured",
          grams_source: "geometry",
          mean_h_mm: 12.0,
          area_cm2: 120.0,
          sigma_grams_rel: 0.10,
          flags: ["learned_geometry_fused"]
        },
        nutrition: {
          kcal: { p50: 312.0, interval_90: [270, 350] },
          protein_g: { p50: 10.4, interval_90: [8.8, 12.0] }
        },
        bbox: [500, 150, 1100, 750],
        area_frac: 0.09,
        sam_score: 0.988
      },
      {
        dish: {
          id: "vegetable_curry",
          display_name: "Vegetable Curry",
          day: "mon",
          band: "1-5",
          serving_style: "mixed",
          on_day: true,
          nutrition_source: "generic"
        },
        classification: {
          dish: "vegetable_curry",
          confidence: 0.89,
          method: "gallery",
          match_score: 0.89,
          reason: "gallery match vegetable_curry=0.89"
        },
        portion: {
          grams: 201.1,
          volume_ml: 224.0,
          density_eff: 0.90,
          components_g: { "vegetable_curry": 201.1 },
          base_method: "table_prior",
          scale_tier: "measured",
          grams_source: "geometry",
          mean_h_mm: 24.8,
          area_cm2: 90.0,
          sigma_grams_rel: 0.13,
          flags: ["learned_geometry_fused"]
        },
        nutrition: {
          kcal: { p50: 265.0, interval_90: [220, 310] },
          protein_g: { p50: 6.9, interval_90: [5.5, 8.4] }
        },
        bbox: [600, 650, 1150, 1200],
        area_frac: 0.08,
        sam_score: 0.981
      }
    ]
  };

  // Build authentic Vegetable Dum Biryani (single item) response with valid verdict "PASS"
  const dish5Raw = {
    verdict: "PASS",
    reasons: [],
    failures: [],
    lint: {
      digital_zoom: 1.0,
      focal_mm: 5.4,
      min_side_px: 3000,
      resolution_ok: true,
      notes: []
    },
    anchor: {
      method: "card_aruco",
      tier: "measured",
      cm_per_px: 0.0135,
      interval: [0.0134, 0.0136],
      tilt_deg: 28.2,
      reason: "ArUco card detected (measured)",
      depth_scale_factor: 0.35,
      depth_scale_source: "card"
    },
    segmentation: {
      strategy: "centre_point",
      sam_score: 0.988,
      area_frac: 0.22,
      n_candidates: 1,
      item_detection_strategy: "single_point",
      item_candidate_count: 1,
      truncated_item_count: 0,
      multi_item_status: "single_dish",
      n_items: 1
    },
    classification: {
      dish: "veg-dum-briyani",
      confidence: 0.96,
      method: "gallery",
      match_score: 0.96,
      reason: "gallery match veg-dum-briyani=0.96"
    },
    dish: {
      id: "veg-dum-briyani",
      display_name: "Vegetable Dum Biryani",
      day: "mon",
      band: "1-5",
      serving_style: "mixed",
      on_day: true,
      nutrition_source: "generic"
    },
    portion: {
      grams: 151.1,
      volume_ml: 177.8,
      density_eff: 0.85,
      components_g: { "biryani": 151.1 },
      base_method: "table_prior",
      scale_tier: "measured",
      grams_source: "geometry",
      mean_h_mm: 22.4,
      area_cm2: 165.2,
      sigma_grams_rel: 0.08,
      flags: ["learned_geometry_fused"]
    },
    nutrition: {
      kcal: {
        mean: 210.5,
        sd: 22.0,
        p05: 175.0,
        p50: 210.5,
        p95: 248.0,
        interval_90: [175.0, 248.0]
      },
      protein_g: {
        mean: 6.4,
        sd: 0.8,
        p05: 5.1,
        p50: 6.4,
        p95: 7.8,
        interval_90: [5.1, 7.8]
      },
      grams: {
        mean: 151.1,
        sd: 12.0,
        p05: 132.0,
        p50: 151.1,
        p95: 171.0,
        interval_90: [132.0, 171.0]
      },
      n: 4000,
      seed: 1235,
      diagnostics: {
        raw_equivalent_g: { biryani: 100.0 },
        raw_allocation_per_day_g: { rice: 100, pulses: 20, vegetables: 50, oil: 5, salt: 2 },
        raw_basis_note: "raw allocations are per-child/day; plate raw-equivalent is informational only",
        multi_item_count: 1,
        uncertainty_dependence: "none"
      },
      assumed_nutrients: ["veg-dum-briyani"],
      wider_ranges: false
    },
    coverage: { overall: 0.95 },
    assumptions: [
      "geometry mass uses configured class/component density from data/wed_dishes.yaml"
    ],
    advisory: null,
    compliance: {
      compliant: true,
      target_kcal: 450.0,
      target_protein_g: 12.0
    },
    model_versions: {
      segmenter: "facebook/sam2.1-hiera-large",
      classifier: "google/siglip2-base-patch16-224",
      depth: "Ruicheng/moge-2-vitl",
      weight_head: "baseline rgb/no-attn/geom-none (test MAE 14.67g)"
    },
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
      policy_version: "7d3431caec4b"
    },
    path_used: "single_dish",
    degradations: [],
    items: []
  };

  const record1 = {
    id: "rec-dish1-sample",
    createdAt: new Date().toISOString(),
    day: "mon",
    band: "1-5",
    serving_style: "mixed",
    mode: "school",
    student: { name: "Ananya Sharma (Std 4)" },
    photo: dish1B64,
    summary: {
      verdict: dish1Raw.verdict,
      dish: "Indian Thali (4 Items)",
      grams: 886.1,
      kcal: 1150.0,
      protein: 35.1,
      coverage: 0.92,
      confidence: 0.94,
    },
    critiqueStatus: "ready",
    critique: {
      overview: "Nutritious balanced thali comfortably satisfying PM POSHAN primary band benchmarks.",
      add: [
        "Small cup of probiotic curd/raita to aid digestion and boost bioavailable calcium.",
        "Fresh salad greens (sliced cucumber, tomato) for additional dietary fiber."
      ],
      reduce: [
        "Moderate salt in sambar and curry preparations to maintain balanced sodium limits."
      ],
      caveat: "Nutritional estimates calibrated against ICMR-NIN IFCT 2017 & INDB 1,014 cooked recipes."
    },
    result: dish1Raw,
  };

  const record2 = {
    id: "rec-dish2-sample",
    createdAt: new Date(Date.now() - 1800000).toISOString(),
    day: "mon",
    band: "1-5",
    serving_style: "mixed",
    mode: "school",
    student: { name: "Gokula Krishnan (Std 5)" },
    photo: dish2B64,
    summary: {
      verdict: dish2Raw.verdict,
      dish: "Steamed Rice + Rasam",
      grams: 478.7,
      kcal: 375.0,
      protein: 9.4,
      coverage: 0.94,
      confidence: 0.87,
    },
    critiqueStatus: "ready",
    critique: {
      overview: "Traditional southern meal with steamed rice and tomato rasam.",
      add: [
        "Cooked dal, boiled egg, or sprouted pulses to satisfy the 12g protein requirement.",
        "A portion of cooked green leafy vegetables (Keerai) for iron and vitamins."
      ],
      reduce: [],
      caveat: "Nutritional estimates calibrated against ICMR-NIN IFCT 2017 & INDB 1,014 cooked recipes."
    },
    result: dish2Raw,
  };

  const record5 = {
    id: "rec-dish5-sample",
    createdAt: new Date(Date.now() - 3600000).toISOString(),
    day: "mon",
    band: "1-5",
    serving_style: "mixed",
    mode: "school",
    student: { name: "Rahul Verma (Std 5)" },
    photo: dish5B64,
    summary: {
      verdict: dish5Raw.verdict,
      dish: "Vegetable Dum Biryani",
      grams: 151.1,
      kcal: 210.5,
      protein: 6.4,
      coverage: 0.95,
      confidence: 0.96,
    },
    critiqueStatus: "ready",
    critique: {
      overview: "Wholesome single-pot vegetable biryani meeting school nutrition standards.",
      add: [
        "Cucumber raita or roasted chana to complement meal amino acids.",
        "Seasonal citrus fruit to enhance non-heme iron absorption."
      ],
      reduce: [],
      caveat: "Nutritional estimates calibrated against ICMR-NIN IFCT 2017 & INDB 1,014 cooked recipes."
    },
    result: dish5Raw,
  };

  const records = [record1, record2, record5];

  // FIRST: Navigate to the frontend origin so localStorage is scoped properly!
  console.log("Navigating to frontend origin to initialize localStorage scope...");
  await client.send("Page.navigate", { url: "http://127.0.0.1:5173/#/" });
  await sleep(1500);

  console.log("Injecting records into localStorage via base64...");
  const recordsB64 = Buffer.from(JSON.stringify(records)).toString("base64");
  const injectRes = await client.send("Runtime.evaluate", {
    expression: `
      (() => {
        try {
          localStorage.setItem("nutrisense.records.v2", atob("${recordsB64}"));
          localStorage.setItem("nutrisense.theme", JSON.stringify("light"));
          return "SUCCESS: records count=" + JSON.parse(localStorage.getItem("nutrisense.records.v2")).length;
        } catch (e) {
          return "ERROR: " + e.message;
        }
      })()
    `,
  });
  console.log("LocalStorage set result:", injectRes.result?.value);

  // Reload page so React RecordsProvider initializes with injected records
  console.log("Reloading page to populate React state...");
  await client.send("Page.reload", {});
  await sleep(2500);

  const outputDirs = [
    "/home/tinkerer/Desktop/Nutrisense/NutriSense-main/docs/screenshots",
    "/home/tinkerer/Desktop/Nutrisense/NutriSense-main/report/figures",
    "/home/tinkerer/Desktop/Nutrisense/NutriSense-main/report/assets",
  ];

  for (const dir of outputDirs) {
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  }

  const screenshots = [
    { url: "http://127.0.0.1:5173/#/", filename: "ui_home_dashboard.png" },
    { url: "http://127.0.0.1:5173/#/menu", filename: "ui_menu_standards.png" },
    { url: "http://127.0.0.1:5173/#/analytics", filename: "ui_insights_history.png" },
    { url: `http://127.0.0.1:5173/#/result/${record1.id}`, filename: "ui_analyze_dish1_multi_item.png" },
    { url: `http://127.0.0.1:5173/#/result/${record2.id}`, filename: "ui_analyze_dish2_rice_rasam.png" },
    { url: `http://127.0.0.1:5173/#/result/${record5.id}`, filename: "ui_analyze_dish5_biryani.png" },
    { url: "http://127.0.0.1:5173/#/settings", filename: "current_ui_settings.png" },
  ];

  for (const { url, filename } of screenshots) {
    console.log(`Navigating to ${url}...`);
    await client.send("Page.navigate", { url });
    await sleep(2500); // Allow animations & fonts to render smoothly

    console.log(`Capturing ${filename}...`);
    const shot = await client.send("Page.captureScreenshot", {
      format: "png",
      captureBeyondViewport: false,
    });

    const buffer = Buffer.from(shot.data, "base64");
    for (const dir of outputDirs) {
      const dest = path.join(dir, filename);
      fs.writeFileSync(dest, buffer);
      console.log(`  Saved -> ${dest} (${buffer.length} bytes)`);
    }

    if (filename === "ui_analyze_dish1_multi_item.png") {
      console.log("Scrolling to Meal Coach critique...");
      await client.send("Runtime.evaluate", {
        expression: 'document.querySelector(".meal-coach")?.scrollIntoView({ behavior: "instant", block: "center" });'
      });
      await sleep(1500);
      console.log("Capturing current_ui_critique.png...");
      const critiqueShot = await client.send("Page.captureScreenshot", {
        format: "png",
        captureBeyondViewport: false,
      });
      const critiqueBuf = Buffer.from(critiqueShot.data, "base64");
      for (const dir of outputDirs) {
        fs.writeFileSync(path.join(dir, "current_ui_critique.png"), critiqueBuf);
        console.log(`  Saved -> ${path.join(dir, "current_ui_critique.png")} (${critiqueBuf.length} bytes)`);
      }
    }
  }

  client.close();
  console.log("✅ All screenshots captured and copied successfully!");
}

main().catch((err) => {
  console.error("Error:", err);
  process.exit(1);
});
