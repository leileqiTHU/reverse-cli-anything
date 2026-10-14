# Example index

These optional showcases demonstrate outcomes produced with the framework. They are not core dependencies, a fixed supported-software list or mandatory acceptance fixtures. Framework installation works without them. [Generic installation](install.md) · [Build another target](SOP.md) · [Watch the unified English demo gallery](demos/README.md).

| Application | Practical agent task | Video | Scope and evidence |
| --- | --- | --- | --- |
| CapCut | Turn real spoken footage into an edited video with music, bilingual captions, transforms and native export | [4:08 MP4](../capcut-cli/assets/capcut-cli-demo.mp4) | [Commands](../capcut-cli/README.md) · [Recorded run: 26 checks](../capcut-cli/evidence/recorded-real-media-20261014.json) · Windows 9.5.0.4050 |
| Axure RP | Build an interactive login prototype with pages, inputs, buttons, validation/navigation, native persistence and HTML export | [1:46 MP4](../axure-cli/assets/axure-cli-demo.mp4) | [Commands](../axure-cli/README.md) · [29 native checks](../axure-cli/evidence/native-login-acceptance.json) · [14 browser checks](../axure-cli/evidence/native-login-browser.json) · Windows 11.0.0.4150 |
| Shapr3D | Build a mounting plate, change thickness and hole spacing, drill a through-hole and export a native project and STL | [0:56 MP4](../shapr3d-cli/assets/shapr3d-cli-demo.mp4) | [Commands](../shapr3d-cli/README.md) · [78 geometry checks](../shapr3d-cli/evidence/recorded-demo-english-20261014.json) · Windows 26.180.11926.0 |

Machine-readable capability index: [registry.json](../registry.json). Video provenance, chapters, checksums and presentation validation: [demo manifest](demos/manifest.json). Media credits: [CREDITS.md](demos/CREDITS.md).

## Evidence boundaries

The native application performs editing, persistence and export. Helper operations such as speech transcription, translation, media decoding and independent geometry checks are identified explicitly. Packaging the videos does not rerun native edits.

CapCut's recorded workflow includes fresh speech recognition and agent-authored Chinese translation. Axure's native HTML is exercised through code-filled inputs and keyboard activation, without modifying its business logic. Shapr3D's current visible tools are scoped to the XY plate example and use native Low-resolution STL; arbitrary sketch construction and general project navigation are not implemented. The drilling recording does not claim a cold app restart.

## Earlier selection research

The [initial candidate report](research/next-example-20261013.md) records the original task and interface analysis. Shapr3D has since completed its scoped modeling example; FL Studio remains unimplemented.

The [closed-source shortlist](research/closed-source-shortlist-20261013.md) compares Axure RP, DxO PhotoLab and CLIP STUDIO PAINT. Axure has since completed the prototype workflow above. Candidates are not listed as supported before implementation and native acceptance.
