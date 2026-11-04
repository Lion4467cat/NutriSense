import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { API_BASE, createClient } from "./services/api";
import { IS_DEMO_MODE } from "./services/mode";
import { createSafeWebStorage } from "./services/storage";
import "@fontsource-variable/inclusive-sans";
import "@fontsource-variable/inclusive-sans/wght-italic.css";
import "@fontsource-variable/jetbrains-mono";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/shell.css";
import "./styles/ui.css";
import "./styles/pages.css";
import "./styles/onboarding.css";
import "./styles/fx.css";
import "./styles/design-system.css";

// composition root: real adapters for persistence and IO
const storage = createSafeWebStorage();
const root = createRoot(document.getElementById("root")!);
const render = (client: ReturnType<typeof createClient>) => root.render(
  <React.StrictMode>
    <App storage={storage} client={client} />
  </React.StrictMode>,
);

if (IS_DEMO_MODE) {
  void import("./services/demoClient").then(({ createDemoClient }) => {
    render(createDemoClient());
  });
} else {
  render(createClient({
    base: API_BASE,
    fetch: window.fetch.bind(window),
  }));
}
