import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { API_BASE, createClient } from "./services/api";
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

// composition root: real adapters for persistence and IO
const storage = createSafeWebStorage();
const client = createClient({
  base: API_BASE,
  fetch: window.fetch.bind(window),
});

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App storage={storage} client={client} />
  </React.StrictMode>
);
