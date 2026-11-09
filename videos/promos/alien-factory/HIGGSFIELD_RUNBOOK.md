# Higgsfield runbook

Use the continuity storyboard and prompt bible as references. The available
connector currently creates 1080p images and short source clips, not native 4K
masters.

## AF-01: Arrival

Image prompt:

> Cinematic hard-science-fiction realism, wide establishing shot of Factory
> Kestrel descending onto an obsidian basalt plain on an alien continent. The
> factory has three white ceramic towers, a low hexagonal graphite operations
> ring, and amber landing beacons. Dust rolls beneath modular landing
> structures; wet ground reflects the lights. A monumental electrically charged
> hurricane wall fills the horizon. Cyan and violet translucent ribbon-like
> organisms remain distant. Immense practical scale, restrained teal-and-amber
> grade, coherent architecture, no text, logo, watermark, humanoid aliens, or
> franchise design.

Motion prompt:

> Slow aerial push toward Factory Kestrel as the descending modules settle.
> Dust expands naturally beneath them, amber beacons pulse subtly, and the storm
> wall advances almost imperceptibly. Preserve tower geometry and horizon.

## AF-02: The scan looks back

Image prompt:

> Factory Kestrel on a dark wet basalt plain at blue hour, with three white
> ceramic towers and a low hexagonal graphite operations ring. A narrow cyan
> scanner sheet crosses a coherent flock of translucent ribbon-like alien
> organisms. The flock is beginning to orient toward the active scanner. A
> small quiet reference station sits dark in the far east. Cinematic
> hard-science-fiction realism, stable geography, no text, logos, watermark,
> humanoids, or fantasy design.

Motion prompt:

> Begin with a slow restrained orbit around the scanner. The cyan sheet sweeps
> once from left to right. Only after it reaches the flock, the ribbon organisms
> turn and drift toward the active station while the distant reference station
> remains unchanged. No rapid morphing.

## AF-04: Storm lock

Image prompt:

> Ground-level cinematic view of Factory Kestrel entering storm lock on an alien
> basalt plain. The same three white ceramic towers rise from the same low
> hexagonal graphite ring. Heavy shutters are partly closed, amber landing
> beacons glow through airborne dust, and coherent translucent ribbon organisms
> cluster near warm exhaust vents. Charged storm clouds fill the sky. Wet,
> practical, restrained hard-science-fiction realism, no text, logos, watermark,
> weapons, or franchise design.

Motion prompt:

> Slow ground-level push toward the operations ring. Shutters close with heavy
> mechanical motion, tower braces settle, dust races laterally in storm wind,
> and the organisms gather around the warm exhaust without changing anatomy.

## Generation sequence

1. Generate each image at 16:9 and 1080p.
2. Review continuity before animating. Reject extra towers, changed factory
   geometry, humanoid organisms, or baked-in text.
3. Animate accepted images for 8-10 seconds with the matching motion prompt.
4. Download immediately to
   `D:\Dev\Data\Gyre\videos\alien-factory\source-clips`.
5. Record request IDs, local SHA-256 hashes, and native dimensions in
   `RENDER_RECEIPTS.md`.
6. Upscale accepted clips to 3840x2160 in a separate finishing pass and record a
   new receipt for each master.
