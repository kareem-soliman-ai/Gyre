# Gyre video studio

This folder contains the small, reviewable production assets for Gyre videos:
scripts, storyboards, captions, prompts, source manifests, and generation
receipts.

Large media files do **not** belong in the Git repository. Raw and rendered
assets live at:

```text
D:\Dev\Data\Gyre\videos
```

See [`data_pointer.txt`](data_pointer.txt). Video binaries are also ignored as a
second line of defence.

## Production slate

| Series | Purpose | Production file |
|---|---|---|
| The Challenge | Explain the Alien Factory objective and score | [`explainers/01-the-challenge.md`](explainers/01-the-challenge.md) |
| Loop Engineering | Teach sensor, controller, state, action, and terminal design | [`explainers/02-loop-engineering.md`](explainers/02-loop-engineering.md) |
| Measurement Changes Worlds | Explain observer effects and objective outcomes | [`explainers/03-measurement-changes-worlds.md`](explainers/03-measurement-changes-worlds.md) |
| Honest Scoreboards | Explain receipts and verification classes | [`explainers/04-honest-scoreboards.md`](explainers/04-honest-scoreboards.md) |
| The Human-AI Dance | Explain capability-sensitive authority | [`explainers/05-human-ai-dyad.md`](explainers/05-human-ai-dyad.md) |
| Alien Factory promos | Short cinematic hooks | [`promos/alien-factory/SHOT_LIST.md`](promos/alien-factory/SHOT_LIST.md) |

Continuity storyboard:
[`assets/alien-factory-storyboard-v1.png`](assets/alien-factory-storyboard-v1.png).

## NotebookLM

Do not upload the entire repository into one notebook. Use the three bounded
source packs in [`notebooklm/SOURCE_MANIFEST.md`](notebooklm/SOURCE_MANIFEST.md):

1. loop and measurement foundations;
2. challenge, scoring, and verification;
3. Alien Factory narrative and observer effects.

That separation reduces source collisions and makes generated narration easier
to fact-check.

## Resolution and provenance

The Higgsfield generation surface available during initial production outputs
1080p source images and short source clips. These are not honestly describable
as native 4K. A 4K release should use those clips as sources, upscale to
3840x2160 in a separate finishing pass, and record both source and master hashes.

Every generated asset should have a row in
[`promos/alien-factory/RENDER_RECEIPTS.md`](promos/alien-factory/RENDER_RECEIPTS.md).
The exact Higgsfield generation sequence is in
[`promos/alien-factory/HIGGSFIELD_RUNBOOK.md`](promos/alien-factory/HIGGSFIELD_RUNBOOK.md).
