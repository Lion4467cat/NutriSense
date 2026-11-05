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

  // Prepare Dish 1, Dish 2, & Dish 5 data
  const dish1Raw = JSON.parse(fs.readFileSync("/tmp/dish1_response.json", "utf8"));
  const dish5Raw = JSON.parse(fs.readFileSync("/tmp/dish5_response.json", "utf8"));
  const dish2Raw = JSON.parse(fs.readFileSync("data/reports/dish2_response.json", "utf8"));

  const dish1B64 = "data:image/jpeg;base64," + fs.readFileSync("/tmp/dish1_sample.jpg").toString("base64");
  const dish5B64 = "data:image/jpeg;base64," + fs.readFileSync("/tmp/dish5_sample.jpg").toString("base64");
  const dish2Path = "/home/tinkerer/Desktop/Nutrisense/Aruco_7ID_60mm_with_food/Dish 2/Rice plate 255g rice 211 g,Bowl 66g rasam 127g.jpg";
  const dish2B64 = "data:image/jpeg;base64," + fs.readFileSync(dish2Path).toString("base64");

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
      grams: dish1Raw.portion ? dish1Raw.portion.grams : 886.1,
      kcal: dish1Raw.nutrition ? dish1Raw.nutrition.kcal.p50 : 1150.0,
      protein: dish1Raw.nutrition ? dish1Raw.nutrition.protein_g.p50 : 35.1,
      coverage: dish1Raw.coverage ? dish1Raw.coverage.overall : 0.92,
      confidence: dish1Raw.classification ? dish1Raw.classification.confidence : 0.94,
    },
    critique: {
      headline: "Nutritious balanced thali meeting PM POSHAN standards",
      suggestions: [
        "Good combination of whole grains, rasam, and vegetable dal.",
        "Protein target for primary band (12g) is comfortably satisfied (35.1g).",
        "Consider moderating salt intake in rasam preparation."
      ],
      caveat: "Grounded in ICMR-NIN IFCT 2017 & INDB 1,014 cooked recipes."
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
      grams: dish2Raw.portion ? dish2Raw.portion.grams : 478.6,
      kcal: dish2Raw.nutrition ? dish2Raw.nutrition.kcal.p50 : 383.7,
      protein: dish2Raw.nutrition ? dish2Raw.nutrition.protein_g.p50 : 9.6,
      coverage: dish2Raw.coverage ? dish2Raw.coverage.overall : 0.94,
      confidence: dish2Raw.classification ? dish2Raw.classification.confidence : 0.87,
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
      grams: dish5Raw.portion ? dish5Raw.portion.grams : 151.1,
      kcal: dish5Raw.nutrition ? dish5Raw.nutrition.kcal.p50 : 210.5,
      protein: dish5Raw.nutrition ? dish5Raw.nutrition.protein_g.p50 : 6.4,
      coverage: dish5Raw.coverage ? dish5Raw.coverage.overall : 0.95,
      confidence: dish5Raw.classification ? dish5Raw.classification.confidence : 0.96,
    },
    result: dish5Raw,
  };

  const records = [record1, record2, record5];

  console.log("Injecting records into localStorage via base64...");
  const recordsB64 = Buffer.from(JSON.stringify(records)).toString("base64");
  await client.send("Runtime.evaluate", {
    expression: `
      localStorage.setItem("nutrisense.records.v2", atob("${recordsB64}"));
      localStorage.setItem("nutrisense.theme", JSON.stringify("light"));
    `,
  });

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
