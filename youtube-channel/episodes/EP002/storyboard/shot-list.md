# EP002 — revised visual storyboard and shot list

This storyboard supersedes earlier fallback suggestions that admitted generic industrial footage. No generic footage is permitted. The same stock source file or source URL may appear once maximum across the entire episode.

| Beat | Exact moving-footage search query | Relevance test | Three.js fallback when no approved footage exists |
|---|---|---|---|
| 01 — Cold open / tin plasma | laser-produced plasma EUV tin droplet source two laser pulses high speed | Must visibly show a laser interacting with a metal/tin droplet or documented EUV source footage. A generic laser cutter is not a match. | section_01: cinematic tin droplet, first shaping pulse, second high-energy pulse, expanding plasma and emitted EUV burst |
| 02 — Chip layers | silicon wafer semiconductor multilayer fabrication wafer handling cleanroom | Wafer / semiconductor process must be identifiable in the actual frame. | section_02: rotating wafer with separated interconnect layers and alignment references |
| 03 — DUV and EUV | EUV lithography optical source extreme ultraviolet semiconductor optics laboratory | Must be relevant to lithography optics or a documented EUV source. | section_03: wavelength comparison, 193 nm DUV and 13.5 nm EUV, with scale caveat |
| 04 — Tin source engineering | ASML EUV light source tin droplet plasma source official video | Use manufacturer-identified source only when the actual subject and license are clear. | section_04: 25 µm conceptual tin target, two pulses, plasma expansion and repeat-cycle context |
| 05 — Mirrors and vacuum | EUV multilayer molybdenum silicon mirror vacuum chamber optics | Must show relevant EUV mirror coating, vacuum optics or verified supplier footage. | section_05: multilayer mirror stack and reflected photon path inside a vacuum chamber |
| 06 — Reticle to wafer | EUV reflective reticle photomask wafer photoresist lithography | Must show a reticle, photoresist wafer or clearly documented EUV exposure process. | section_06: reflective reticle, reduction optics and patterned exposure on wafer |
| 07 — Wafer stage | ASML wafer stage metrology interferometer lithography scanner | Must show an identifiable precision wafer stage or metrology system. | section_07: moving wafer stage, actuator ring and measurement feedback beams |
| 08 — Repeated process cycle | semiconductor deposition etch lithography wafer inspection production line | Every selected shot must visibly match the named process; do not reuse a generic cleanroom shot. | section_08: wafer moving once through deposition, lithography, etch and inspection tools |
| 09 — High-NA EUV | ASML EXE 5000 High NA EUV scanner Intel cleanroom official footage | Do not imply a generic scanner is the EXE:5000 or that an exact Intel production line is shown. | section_09: 0.33 versus 0.55 numerical-aperture ray cones, explicitly conceptual |
| 10 — Ecosystem payoff | semiconductor fab wafer transport robotics lithography metrology process equipment | Show only the process or equipment actually visible; each source can be used once. | section_10: laser, optics, sensors, motion systems, reticle, resist and process tools interconnected around a wafer |

## Edit decisions

- Opening frame must be the Three.js tin-plasma sequence unless a visually verified, rights-cleared recording of that exact process is approved. A tractor or generic laser cutter is never acceptable.
- Remove every clip currently classed as irrelevant, generic, context-only or visually unreviewed. Do not simply trim it, recolour it or use another timestamp from the same source.
- Use source URL plus SHA-256 to enforce the one-appearance rule globally.
- A source that fails review is not eligible for another scene.
- Stock assets must be moving, relevant and rights-cleared. Still images do not count as B-roll.
- Use Three.js motion diagrams for missing mechanisms, not slides. Keep the red/white/blue brand treatment restrained and keep labels attached to moving imagery.
- Captions must be legible and actually burned into the final picture; keep a separate SRT sidecar.
- Report actual timeline duration by visual type. Until verified, report B-roll as unapproved / not counted.
