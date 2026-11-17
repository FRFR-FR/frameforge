# LOOMWILD: OFFLINE PvP — first A-scope prototype

**Platform:** Android only  
**Game mode:** Offline 1v1, one human player versus one fully automated bot  
**Internal render target:** 1280 × 720, 30 FPS cap  
**Map:** One medium-sized Loomwild combat arena  
**Engine:** Godot 4.4.1, Compatibility renderer

## Match contents

- Ten original, separately modelled and exported guns: Vesper-9, Flux SMG, Aegis AR, Kestrel Burst, Ranger DMR, Longbow, Breach-12, Bastion LMG, Pulse Carbine and Arc Lance.
- Two flash grenades per fighter and one timed cyber-shield ability with a cooldown.
- No melee weapons, explosives other than flash grenades, healing pickups, vehicles, currencies, accounts or online systems.
- The player and bot use the ten existing Loomglass character designs. The build re-exports each skinned GLB with its original idle plus Wave, Guard and Victory emotes.
- The bot can engage, aim and fire, run, strafe, flank, reload, throw flash grenades, move to cover, hide and activate its cyber shield.
- The match ends when one fighter is defeated. REMATCH resets both fighters, ammunition and abilities on the same map.

## Mobile controls

Use RUN / LEFT / BACK / RIGHT to move. Drag on the right side of the screen to aim. Hold FIRE to shoot. FLASH throws a flash grenade. CYBER SHIELD activates the defensive barrier. RELOAD and NEXT GUN manage the weapon. EMOTE 1–3 play the character emotes.

## GitHub-only build

The workflow checks out the character and world source branches, installs Blender, Godot, Java and the Android SDK on temporary GitHub runners, regenerates all assets, verifies the files, runs a Godot gameplay smoke test and exports an Android debug APK. No local installation is required.

The Blender asset build performs a clean automatic retry once after a generation or audit failure. The Godot import/test/export stage also gets one clean-import retry. Persistent source-code defects still fail the workflow and are reported in its logs; CI cannot safely rewrite unknown gameplay code by itself.

## Asset and quality gates

- Ten named character GLBs, each with a humanoid skeleton, skinned mesh, idle animation and three emote clips.
- Ten distinct weapon GLBs with meshes and authored materials.
- One Loomwild world GLB and its source audit.
- Character and weapon presentation previews at exactly 1280 × 720.
- Godot headless import, match-spawn, AI-state, ten-weapon, defeat and rematch tests before APK export.
- Android export only. Internet, camera and microphone permissions are disabled in the Android preset.
- Every uploaded build and QA report requests 90-day artifact retention.

## Scope boundary

This is an A-scope indie prototype, not an AA/AAA production. The workflow can prove source integrity, asset structure, gameplay startup, core match logic and APK export. It cannot certify performance on every physical Android phone. Device-specific frame-rate, thermal, touch-latency and visual QA still need to be checked on a real phone before calling the prototype release-ready. The APK produced by CI is a debug/testing build, not a store-signed release.
