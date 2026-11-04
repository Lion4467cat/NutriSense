import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AppProvider } from "../context/AppContext";
import { PREFS_KEY } from "../context/prefs";
import { createDemoClient } from "../services/demoClient";
import { createMemoryStorage } from "../services/storage";
import AnalyzePage from "./Analyze";
import ResultPage from "./Result";

vi.mock("../utils/image", () => ({ fileToThumbnail: async () => "data:image/jpeg;base64,demo" }));

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("demo upload-to-result journey", () => {
  it("uploads a photo, saves a mock response, and shows item weights and meal uncertainty", async () => {
    const NativeURL = URL;
    class TestURL extends NativeURL {
      static createObjectURL = () => "blob:demo-photo";
      static revokeObjectURL = vi.fn();
    }
    vi.stubGlobal("URL", TestURL);
    vi.stubGlobal("crypto", { randomUUID: () => "demo-record" });
    const storage = createMemoryStorage({ [PREFS_KEY]: JSON.stringify({ mode: "school" }) });
    const client = createDemoClient();

    render(
      <AppProvider storage={storage} client={client}>
        <MemoryRouter initialEntries={["/analyze"]}>
          <Routes>
            <Route path="/analyze" element={<AnalyzePage />} />
            <Route path="/result/:id" element={<ResultPage />} />
          </Routes>
        </MemoryRouter>
      </AppProvider>,
    );

    expect(await screen.findByLabelText("Day")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Upload meal photo"), {
      target: { files: [new File(["sample"], "meal.jpg", { type: "image/jpeg" })] },
    });
    fireEvent.click(screen.getByRole("button", { name: "Analyze this meal" }));

    expect(await screen.findByText("Meal weight")).toBeInTheDocument();
    expect(screen.getByText("Steamed rice")).toBeInTheDocument();
    expect(screen.getByText("Sambar")).toBeInTheDocument();
    expect(screen.getByText("Vegetable salad")).toBeInTheDocument();
    expect(screen.getByText(/90% interval 360–560 g/)).toBeInTheDocument();
    expect(screen.getByText(/Relative SD 18%/)).toBeInTheDocument();
  });
});
