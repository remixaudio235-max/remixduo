# V8.31 — Remix Dou branding in running Smaart toolbar

Date: 2026-10-30 / Admin-PC
Source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA
Scope: Source-code UI only. No image mockup is substituted for the running GUI.

## Implementation
- signal_tools_gui_v813.py / ToolHub now adds a QWidget brand strip to the LEFT of the current Auto Phase button.
- Logo: remix_dou_swirl_toolbar32.png, extracted from the user's provided RemiX Audio Tune logo and resized as a transparent 32px asset.
- Label text: "Remix Dou", bold white.
- The native tool buttons retain their original anchoring: when Smaart row is verified, toolbar expands 125px LEFT and leaves the preexisting 205px buttons at the same screen coordinates.
- Legacy construction width remains 205px until first placement, and brand is hidden for the fallback menu in very narrow layouts.
- Button callbacks and saved TF / generator / soundcard / DSP remain unchanged.

## Validation
- 41/41 regression tests PASS (including previous Export EQ, plot detection, SUM Phase/Mag and V8.31 geometry).
- Active source restarted with exact wrapper PID 16328 and child PID 18332; Smaart not restarted.
- Screenshot from real Smaart app saved: V831_BRAND_LIVE_QA.png.
- Screenshot visually verifies: small colorful swirl, "Remix Dou" BEFORE Auto Phase; Auto EQ, Xuất EQ, FIR and Smaart Real Time, Impulse, SPL buttons intact.
- SUM Phase, SUM Mag and selected-trace panel continue to render.
- Logo SHA256: F25E294575CFB6730DEDBCA6D9298A3B9F0E67D8227C6832FDF2E3DA33DA5559.

The attached screenshot is evidence of the actual process, not a generated preview.
