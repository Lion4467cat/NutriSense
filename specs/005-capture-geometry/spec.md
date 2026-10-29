# Spec 005: Capture geometry guidance (P2)

- **Status:** partial (guidance implemented; two-shot capture deferred)
- **Date:** 2026-10-29
- **Source:** docs/feasibility.md sensitivity table (depth/base-plane is the
  dominant error term, ±26–33%); ledger 007 (monocular metric zero-point);
  ledger 015 follow-ups.

## Problem Statement

The depth/base-plane term dominates the error budget. Two levers exist that
need no new model: (1) a guided capture angle (oblique enough for base-plane
evidence, not so oblique that area foreshortening dominates), and (2) a
two-shot capture (top + oblique) that turns the monocular zero-point problem
into weak stereo. The app today gives no capture-angle feedback.

## Scope decision

- **Implemented now:** a capture-angle lint. The anchor stage already
  recovers marker tilt; a measured-tier capture whose tilt falls outside the
  recommended band gets an informational `lint.notes` entry (non-blocking,
  same style as the resolution note). Band: 25–60 degrees from face-on,
  a pre-registered default pending the P4 capture protocol's measurements.
- **Deferred:** two-shot capture. It requires an API v2 (two images per
  analysis), a capture-session protocol, and a correspondence/fusion stage.
  That is a hardware-adjacent protocol change, not a library change, and is
  recorded here as the follow-up rather than half-implemented.

## Success criteria (written BEFORE code)

1. Suite green, ruff clean, pyright ≤ baseline.
2. Seam tests: an in-band capture carries no angle note; an out-of-band
   capture carries the note and the verdict path is unchanged.
