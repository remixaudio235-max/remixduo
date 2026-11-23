# RemiX Dou V8.38 — Smaart visible-plot saved smoothing sync

Date: 2026-10-30 / Admin-PC
Active source: D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_27_MAG_NATIVE_SYNC_QA
Starting Git HEAD: 2396794

## Defect
Auto Phase independently offers MAG and PHASE smoothing controls but the
automatic sync from SmaartConfig.xml returned None. Reader hardcoded
Phase1 / Magnitude1 with visible=1. On the actual saved Smaart state:
- Phase1: visible=0, smoothingId=5
- Phase2: visible=1, smoothingId=5
- Magnitude1: visible=1, smoothingId=5
- Magnitude2: visible=0, smoothingId=5
Thus it failed to load a valid Phase smoothing when Smaart used Phase2.

## Focused fix
Read all PhaseN and MagnitudeN plotProperties with visible=1.
Apply independent MAG/PHASE values to corresponding Auto Phase combos
only if there is a unique smoothingId for each visible plot type.
Conflicting active panes or missing/unsupported IDs fail closed.
Preserve existing smoothing IDs and earlier explicit caveat: only ID=5
mapped to 1/6 Oct has been verified on this machine; other IDs remain
provisional. Keep all DSP, complex H(f), Phase/Mag SUM, LF–HF ROI,
Native Y and AutoEQ code unmodified.

## QA
- 6 new visible-pane/ambiguous/unknown-ID tests.
- Focused regression + active V8.36/8.37 suite: 86/86 PASS.
- Actual read-only saved config:
  mag_id=5 phase_id=5 mag_oct=0.1666666667
  phase_oct=0.1666666667 both verified=True.
- Existing refresh interval: 1.5 sec; uses SmaartConfig.xml file
  modification time rather than a live Smaart control subscription.

## Important limitation
This is **saved-config synchronization**, NOT instantaneous UI sync.
Changes made in the live Smaart GUI without saving its configuration
are not guaranteed to update RemiX. Automatic Mag Y pixel matching
in V8.37 also tests 1/6-Oct smoothing, but does not set the Phase
smoothing control. These are separate functions.
No user files or Smaart DSP/audio settings modified.

## Live UI
After a controlled restart of only the RemiX companion, confirm that
both Auto Phase smoothing combos initialize at 1/6 Oct. Preserve the
Smaart executable and other working sessions.
