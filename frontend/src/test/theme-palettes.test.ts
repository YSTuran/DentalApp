import { afterEach, describe, expect, it } from "vitest";

import "../styles.css";

const PALETTE_BACKGROUNDS = [
  { palette: "ocean", light: "#edf4f9", dark: "#0d1720" },
  { palette: "violet", light: "#f4f0f8", dark: "#17131d" },
  { palette: "arctic", light: "#ebf6f8", dark: "#0b1719" },
  { palette: "sage", light: "#eef3ed", dark: "#111812" },
  { palette: "amber", light: "#f9f2e5", dark: "#1b1710" },
  { palette: "burgundy", light: "#f7eef2", dark: "#1b1216" },
  { palette: "coral", light: "#faefed", dark: "#1c1312" },
] as const;

const REQUIRED_SURFACE_TOKENS = [
  "--page-bg",
  "--ink",
  "--muted",
  "--line",
  "--line-soft",
  "--surface",
  "--surface-muted",
  "--surface-soft",
  "--input-bg",
];

afterEach(() => {
  delete document.documentElement.dataset.mode;
  delete document.documentElement.dataset.palette;
});

describe("renk paleti yüzeyleri", () => {
  it.each(PALETTE_BACKGROUNDS)(
    "$palette paleti açık ve karanlık görünümde kendi arka planını kullanır",
    ({ palette, light, dark }) => {
      const root = document.documentElement;
      root.dataset.palette = palette;

      root.dataset.mode = "light";
      let computedStyle = getComputedStyle(root);
      expect(computedStyle.getPropertyValue("--page-bg").trim()).toBe(light);
      for (const token of REQUIRED_SURFACE_TOKENS) {
        expect(computedStyle.getPropertyValue(token).trim()).not.toBe("");
      }

      root.dataset.mode = "dark";
      computedStyle = getComputedStyle(root);
      expect(computedStyle.getPropertyValue("--page-bg").trim()).toBe(dark);
      for (const token of REQUIRED_SURFACE_TOKENS) {
        expect(computedStyle.getPropertyValue(token).trim()).not.toBe("");
      }
    },
  );
});
