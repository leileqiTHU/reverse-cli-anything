# Shapr3D CLI demonstration

[Watch the English edition](assets/shapr3d-cli-demo.mp4) · [Three-case gallery](../docs/demos/README.md)

The current edition opens directly on the empty model. It matches the CapCut and Axure application-above-terminal layout: a dark command footer, Consolas text, cyan headings, white commands, and green results. All added labels are in English. The original application's Chinese UI remains unchanged in the source footage.

**56 seconds, 1920 × 1440, H.264, 30 fps, no audio.** The first 49 seconds preserve the complete original recording at 1× speed. A seven-second final-frame hold presents verification. There is no title card or separate result slide.

## Workflow

| Time | Native operation |
| --- | --- |
| 00:00 | Empty model and CLI session variables |
| 00:03 | Import a rectangular DXF outline and two circles |
| 00:08 | Extrude the plate to 4 mm |
| 00:12 | Change the history parameter to 6 mm |
| 00:17–00:22 | Move both mounting holes; change spacing from 50 to 60 mm |
| 00:26–00:30 | Import the center circle and select its exact native region |
| 00:34–00:42 | Cut 2 mm, deepen to 4 mm, then cut through at 8 mm |
| 00:46 | Export the native .shapr project and STL mesh |
| 00:49 | Show independent geometry verification |

Shapr3D computes the solids and holes. External code supplies only two-dimensional DXF sketches. Original modeling used no mouse clicks or keyboard UI input. This presentation edit did not modify the open project or rerun modeling.

## CLI display and provenance

The footer displays **28 full native CLI equivalents**, including the executable, `call`, `--session`, `--json`, and operation parameters, plus the independent verification command. This replaces the earlier abbreviated `call({...})` panel.

The original recording was driven by `full_demo.py`, which submits requests to the same native bridge queue used by `pilot.py call`. The displayed PowerShell lines are reconstructed equivalents of verified requests, not a new execution or terminal screen recording. Groups change at the original stage-completion markers. The footer explicitly identifies this presentation method.

`$S`, `$PLATE`, and `$DRILL` are defined at the beginning. Paths use actual PowerShell variable expansion; localized history names retain their exact JSON values through Unicode escapes. The full transcript is at `outputs/presentation-english-20261014/cli-transcript.ps1`. It records a past session: do not replay stale native IDs or existing export destinations blindly.

Original recording: **2026-10-13**. English presentation and independent revalidation: **2026-10-14**. The 1026 × 802, 15 fps source is proportionally enlarged; output at 30 fps duplicates frames without inventing motion.

## Acceptance

- **78/78 independent geometry checks passed** on the recorded native STL.
- Plate: 80 × 40 × 6 mm; original holes: diameter 6 mm, spacing 60 mm; new center hole: diameter 8 mm, through.
- One connected solid, closed manifold, 188 triangles, Euler characteristic −4.
- All 38 original receipts match their journals and succeed; original recording hash unchanged.
- Full MP4 decode: 1,680 frames, 56 seconds. PowerShell transcript parses without errors.
- Encoded-frame review covers all 12 stages and verification. Native image-area SSIM against the source exceeds 0.99.

[Acceptance summary](evidence/recorded-demo-english-20261014.json). Detailed evidence, frame samples, command manifest, and comparison logs are under `outputs/presentation-english-20261014/`.

The native STL uses the account's available Low resolution. This recording does not demonstrate a cold application restart. Source exports remain at `outputs/full-build-visible-20261013/drill/after.shapr` and `after.stl`.

## Rebuild the presentation

Run from the repository root with a fresh MP4 output filename. The packaging script refuses overwrites and does not control Shapr3D. It reuses Pillow and the existing FFmpeg installation on D:.

```powershell
$env:TEMP = 'D:\Caches\Shapr3D\Temp'
$env:TMP = $env:TEMP
python -B shapr3d-cli/verify_drilled_plate.py `
  shapr3d-cli/outputs/full-build-visible-20261013/drill/after.stl `
  --before shapr3d-cli/outputs/full-build-visible-20261013/drill/before.stl `
  --out shapr3d-cli/outputs/presentation-english-20261014/geometry-verification.json

python -B shapr3d-cli/tools/package_recording_english.py `
  --source shapr3d-cli/outputs/full-build-visible-20261013 `
  --work shapr3d-cli/outputs/presentation-english-20261014 `
  --output shapr3d-cli/exports/shapr3d-cli-demo-english-new.mp4
```

Packaging requires the original MP4, both `job.json` files, and receipts under `.runtime/sessions/full-demo-20261013`. The prior 63-second Chinese presentation is retained as `exports/shapr3d-cli-demo-20261014.mp4`; the English edition above is the current showcase version. See [the native recording guide](VISIBLE-DRILL-DEMO.md) for the original modeling procedure.
