# Three native CLI demonstrations

| Application | Watch | Workflow | Native acceptance |
| --- | --- | --- | --- |
| CapCut | [MP4 · 4:08](../../capcut-cli/assets/capcut-cli-demo.mp4) | Project, media import, trimming, fresh ASR and translation, music, editable captions, clip transform, native export, reopen and final playback | 26 native/media checks |
| Axure RP | [MP4 · 1:46](../../axure-cli/assets/axure-cli-demo.mp4) | Pages, text, buttons, inputs, layout, click rules, undo/redo, save/cold reopen, native HTML and browser interaction | 29 native + 14 browser checks |
| Shapr3D | [MP4 · 0:56](../../shapr3d-cli/assets/shapr3d-cli-demo.mp4) | DXF sketch import, extrusion, thickness, hole-face moves, central circular cut and native project/STL export | 78 geometry checks |

These curated MP4 files and their JPEG previews live in each adapter's `assets/` directory and are explicitly included by the repository's ignore rules. README links work within the repository and do not rely on local cache paths or an unpublished release URL. No remote upload is part of this packaging task.

## Shared presentation

The presentation specifications below describe the three full demonstrations. The shorter overview has its own format and edit list.

- No opening title card. Each video opens directly on its recorded application workflow.
- 1920 × 1440, H.264, 30 fps; application pixels above a 420-pixel command footer.
- English headings, operation descriptions and status text. Original application UI and content languages remain intact.
- Background `#111827`, Consolas commands at 23 px, bold headings at 26 px, cyan headings, white commands and green success results.
- Original order and speed. Lower-rate recordings are frame-repeated, not motion-interpolated.
- No mouse clicks. Axure's exported prototype is tested using input/change events and keyboard Enter; this is identified in the video.

## What was reused

**CapCut:** 214.733 seconds of the accepted 2026-10-14 Windows Graphics Capture recording, followed by its 33.7-second native export. The footer is rebuilt from the original timed execution log; the agent's fresh Chinese translation wait remains in place. Speech and music play only during the labeled result segment. Recognition, translation and timing were generated during that original run, not regenerated during this presentation edit. [Workflow and source evidence](../../capcut-cli/examples/recorded-real-media.md).

**Axure:** the accepted 2026-10-13 native editor clips and exported-HTML browser capture. The two editor clips contain 1,037 and 194 frames at 15 fps. The browser segment is rebuilt from its 115 original CDP JPEG captures and original duration list into 352 frames, avoiding the old burned-in subtitles. Native CLI commands and browser events come from their original timed journals. The video is silent. [Native prototype acceptance](../../axure-cli/evidence/native-login-acceptance.json) · [Browser acceptance](../../axure-cli/evidence/native-login-browser.json).

**Shapr3D:** the accepted 56-second English edition, copied byte-for-byte. It includes all 49 seconds of the original 2026-10-13 recording and a seven-second final-frame verification hold. Its 28 displayed native CLI calls are PowerShell equivalents reconstructed from verified requests, grouped by completed stage; they are not a new execution or an original terminal recording. The video is silent. [Detailed provenance and limits](../../shapr3d-cli/RECORDED-DEMO.md).

The presentation build does not mutate projects or rerun native editing. Native acceptance counts refer to the evidence above; packaging validation checks the video files, frame counts, audio, captions, imagery and source identity separately. Shapr3D's Low-resolution mesh and scoped plate-modeling limitations remain in effect. A cold restart is shown for Axure, not claimed for the Shapr3D drilling video.

## Verification and chapters

[manifest.json](manifest.json) records each finished file's SHA-256, duration, decoded frame count, source hashes, English chapters, source evidence and presentation checks. Visual review samples cover creation, key edits, export and the final result. The CapCut audio check also distinguishes silent command footage from the audible native result.

Detailed local capture and encoding intermediates remain in `D:\Caches\reverse-cli\showcase-20261014\`; they are not required to play the curated videos.

## Rebuild

The original local recordings and their journals are required. Pillow, Windows Consolas fonts and the existing D-drive FFmpeg are reused; no application is controlled by the packaging script.

```powershell
python -B tools/package-showcase.py --app capcut
python -B tools/package-showcase.py --app axure
python -B tools/package-showcase.py --app shapr3d
python -B tools/check-showcase.py --app capcut
python -B tools/check-showcase.py --app axure
python -B tools/check-showcase.py --app shapr3d
python -B tools/check-layout.py
```

The packager refuses existing output files. Preserve a previous edition separately before an intentional rebuild; do not delete project data or original recordings. Review the generated frames and finish the manifest before treating a new edition as accepted.

## Short overview

[CapCut overview · 45 seconds](../../capcut-cli/assets/capcut-cli-45s.mp4) presents selected segments of the existing full CapCut recording. It is an edited overview, not a continuous 45-second execution. The six excerpts retain their original speed and chronology: project creation (source 5–11 s), timeline editing (38.4–44.4 s), captions (131.85–138.85 s), native export (171.7–177.7 s), save/reopen (186.35–192.35 s), and result playback (223–231 s). A six-second project link and attribution card closes the video.

The overview is 1440 × 1200, H.264/AAC at 30 fps. The new header labels each stage and the edited nature of the presentation. Original command captions and application imagery are preserved; no native operations were rerun. The result excerpt retains its original speech and music. Source acceptance counts belong to the original workflow, not a new test run.

The [README GIF](../../capcut-cli/assets/capcut-cli-teaser.gif) is a silent nine-second selection from overview timestamps 6–9 s, 12–15 s and 33–36 s. It crops away the detailed command footer to keep the application visible at README size, samples at 8 fps and preserves playback speed. Use the linked MP4 or full recording for command details. [Overview file hashes and verification](promotion-manifest.json).

## Media attribution

CapCut's footage and music attribution travels with this gallery: [CREDITS.md](CREDITS.md). The recordings show third-party applications; no application binaries are distributed and no vendor endorsement is implied.
