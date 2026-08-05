import { definePreset } from "@primevue/themes";
import Material from "@primevue/themes/material";

// GuardyMed runs a single light scheme (see styles.css `color-scheme: light`).
// This preset retints PrimeVue's Material theme with the app's existing
// OKLCH primary/surface hues so PrimeVue components (Select, Tag, Toast, ...)
// sit visually inline with the hand-rolled design system instead of
// introducing a second, competing palette.

const primary = {
  50: "oklch(0.97 0.02 190)",
  100: "oklch(0.93 0.035 190)",
  200: "oklch(0.87 0.05 190)",
  300: "oklch(0.79 0.07 190)",
  400: "oklch(0.69 0.085 190)",
  500: "oklch(0.57 0.1 190)",
  600: "oklch(0.5 0.105 190)",
  700: "oklch(0.46 0.11 190)",
  800: "oklch(0.38 0.09 190)",
  900: "oklch(0.3 0.07 190)",
  950: "oklch(0.22 0.05 190)",
};

const surface = {
  0: "#ffffff",
  50: "oklch(0.98 0.004 230)",
  100: "oklch(0.96 0.006 230)",
  200: "oklch(0.91 0.008 230)",
  300: "oklch(0.84 0.01 230)",
  400: "oklch(0.72 0.012 230)",
  500: "oklch(0.6 0.014 230)",
  600: "oklch(0.5 0.012 230)",
  700: "oklch(0.4 0.016 232)",
  800: "oklch(0.3 0.018 235)",
  900: "oklch(0.22 0.02 240)",
  950: "oklch(0.15 0.02 240)",
};

// Solid fills for Tag/Message/Toast "severity" backgrounds need to hold
// >=4.5:1 contrast against white foreground text (WCAG AA, per PRODUCT.md).
// These are deliberately darker than the app's own tint tokens
// (--success/--warning/--danger/--info in styles.css), which are used the
// other way around: a light tint background with dark foreground text.
const solidGreen = "oklch(0.5 0.13 155)";
const solidAmber = "oklch(0.48 0.15 70)";
const solidRed = "oklch(0.52 0.19 28)";
const solidSky = "oklch(0.48 0.1 235)";

export const GuardyMedPreset = definePreset(Material, {
  semantic: {
    primary: {
      ...primary,
      color: "{primary.500}",
      contrastColor: "#ffffff",
      hoverColor: "{primary.600}",
      activeColor: "{primary.700}",
    },
    surface,
    focusRing: {
      width: "2px",
      style: "solid",
      color: "{primary.color}",
      offset: "2px",
      shadow: "0 0 0 4px color-mix(in oklab, {primary.color} 16%, transparent)",
    },
    colorScheme: {
      light: {
        primary: {
          color: "{primary.500}",
          contrastColor: "#ffffff",
          hoverColor: "{primary.600}",
          activeColor: "{primary.700}",
        },
        surface,
      },
    },
  },
  primitive: {
    green: { 500: solidGreen, 400: solidGreen, 950: "#ffffff" },
    orange: { 500: solidAmber, 400: solidAmber, 950: "#ffffff" },
    red: { 500: solidRed, 400: solidRed, 950: "#ffffff" },
    sky: { 500: solidSky, 400: solidSky, 950: "#ffffff" },
  },
});
