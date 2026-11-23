# V8.87 Mac Smaart overlay QA

Exact Windows shared source: `D:\REMIX_AUTO_ALIGN_V6_DEV\windows_v8_87_MAC_OVERLAY_QA`.
Mac source: `/Users/dinhtran/RemiX_Duo_Build/V887/source`.

Mac entry now defaults to a floating 336×36 Smaart-attached toolbar with Auto
Phase/EQ/FIR and 446×400 attached tool panels. Standalone TRF workspace is
explicit `--workspace`/context-menu auxiliary only. Native Cocoa configuration
joins Spaces and allows fullscreen auxiliary windows without activating Smaart
or modifying its audio. Geometry worker16ms is independent of selection worker;
this timer interval is NOT measured follow latency.

Windows51 shared tests PASS; Mac49 PASS2 Windows-onlySKIP. Existing Windows
477 PASS1 frozen-Windows-bundle-unavailableSKIP. Native hidden QNSPanel smoke
PASS (floating level3, collectionBehavior257). Nativearm64 build, bundled assets,
all-binary architecture audit, ad-hoc signature verification and frozen
selfcheck from `/` PASS. Internal QA only; Intel and notarization HOLD.

Actual install from mounted DMG:
`/Users/dinhtran/Applications/RemiXDuo_V887_Overlay_QA_Final.app`.
Desktop installer: `/Users/dinhtran/Desktop/RemiXDuo-8.87-overlay-qa-arm64-final.dmg`.
SHA256 `0f69f71b8721c069619c52f5c8e25faaf44a68ece3e07afc69e23d32e2a2bbbe`.
Running installed PID26168, CWD `/`; no duplicate old observer. Exact preflight
confirmed legacySwift99595 and ownV88621042 paths+CWD before terminating only
those; later source23326 terminated before installed app launch. Smaart18104
and license helper18110 untouched. Existing MAC license preserved.

Live visual/follow HOLD: actual CGSession `CGSSessionScreenIsLocked=True`;
ScreenCaptureKit zero available displays. User unlock request pending. Do not
claim current toolbar visible/follows gestures or current tick accepted.

Native trace tick/file identity, TF/Fs/axes and SUM/MagEQ/FIR rendering remain
HOLD. Panels explain missing evidence and draw no native curves. This is not
complete Windows/Mac feature parity. Active Windows V8.84 remains unchanged.

Next safe action: user unlocks Mac and foregrounds Smaart; capture known
Smaart+own overlay windows, measure reversible move/resize with original geometry
restored. Never start another observer while PID26168 holds the common lock.
