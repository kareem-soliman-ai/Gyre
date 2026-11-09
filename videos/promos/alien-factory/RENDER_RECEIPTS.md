# Alien Factory render receipts

Generated media lives under `D:\Dev\Data\Gyre\videos\alien-factory`. URLs may
expire; local file hashes are the durable identity.

| ID | Source request | Video request | Model | Native output | Local path | SHA-256 | Status |
|---|---|---|---|---|---|---|---|
| Storyboard v1 | built-in image generation | n/a | image generation | 1664x960 PNG | `videos/assets/alien-factory-storyboard-v1.png` | `c8111d582aa76de0d6da13a23fc7e5cdfe2a909242e9bf92427a8b77a93402f7` | complete |
| AF-01 | no request ID issued | pending | Higgsfield | 1080p source target | pending | pending | blocked: connector credential is `<FILL_IN>` |
| AF-02 | no request ID issued | pending | Higgsfield | 1080p source target | pending | pending | blocked: connector credential is `<FILL_IN>` |
| AF-04 | no request ID issued | pending | Higgsfield | 1080p source target | pending | pending | blocked: connector credential is `<FILL_IN>` |

The final 4K master must receive a separate row with its upscaling method and
hash. A generation request ID proves provenance, not visual quality; each clip
still requires human review for continuity, artefacts, and scientific meaning.

On 2026-07-29 both the new and old Higgsfield image endpoints returned HTTP 422
before creating a request because the connector's `hf-api-key` was still the
literal placeholder `<FILL_IN>`. No Higgsfield image or video was generated.
