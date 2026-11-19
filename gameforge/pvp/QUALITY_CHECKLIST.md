# GAMEFORGE BLACKTIDE — PERFECTED PROTOTYPE DAILY ACCEPTANCE CHECK

This is a **completion gate**, not a progress reminder. The prototype is not considered finished until every blocking item passes.

## 1. Build integrity
- [ ] Clean checkout builds without manual file edits.
- [ ] Android package installs and launches.
- [ ] Desktop test build launches.
- [ ] Landscape 16:9 is enforced; portrait is never used.
- [ ] No missing assets, scripts, shaders, textures, fonts, or scenes.
- [ ] No parser errors, runtime errors, or repeated warnings in the final run.

## 2. Player movement — blocking
- [ ] Player physically translates through the world; camera-only movement is forbidden.
- [ ] Left-thumb virtual stick controls continuous acceleration.
- [ ] Friction/deceleration feels controllable rather than instant.
- [ ] Sprint changes movement speed.
- [ ] Crouch changes stance and speed.
- [ ] Jump works where geometry permits.
- [ ] Collision prevents walking through buildings, cover, props, and map boundaries.
- [ ] Player cannot become permanently stuck.
- [ ] Spawn points are reachable and safe.
- [ ] No fixed movement/action button cluster is visible during normal movement.

## 3. Combat — blocking
- [ ] Aim follows right-thumb drag.
- [ ] Firing follows the actual reticle direction.
- [ ] Hits use physical line-of-sight/raycast validation.
- [ ] Weapons have distinct recoil, fire rate, damage and reload behavior.
- [ ] Reload works reliably.
- [ ] Weapon switching works without soft-locks.
- [ ] Hit feedback is visible and readable.
- [ ] Death/respawn/rematch state transitions work.
- [ ] AI opponent can move, seek cover, aim and attack.

## 4. UI
- [ ] Real settings button exists.
- [ ] Settings panel opens and closes.
- [ ] Sensitivity persists.
- [ ] Invert-look persists.
- [ ] Aim-assist setting persists.
- [ ] Volume setting persists.
- [ ] Graphics profile persists.
- [ ] HUD does not obscure the playable environment.
- [ ] UI is readable at 720p landscape.
- [ ] Touch controls are contextual/minimal rather than a permanent button wall.

## 5. World quality
- [ ] Main map is substantially larger than a simple arena.
- [ ] Multiple distinct combat lanes exist.
- [ ] Interior and exterior spaces are both playable.
- [ ] At least two vertical routes exist.
- [ ] Hard cover is distributed throughout the map.
- [ ] Objectives have meaningful spatial separation.
- [ ] Collision proxies cover all major structures.
- [ ] No invisible walls block legitimate routes.
- [ ] No giant empty areas exist without gameplay purpose.
- [ ] Environment has lighting, material variation, signage/hazard language, industrial props and believable scale.

## 6. Character quality
- [ ] Operators are original Blender-authored assets.
- [ ] No primitive-only placeholder characters.
- [ ] Character proportions are humanoid and combat-ready.
- [ ] Distinct silhouettes exist between operators.
- [ ] Face/head, torso, arms, legs, footwear, gloves and equipment read clearly.
- [ ] Skeleton/rig exists.
- [ ] Walk, sprint, crouch, jump, aim and firing poses exist.
- [ ] Weapon sockets align with hands.
- [ ] No foot-through-ground or floating-foot errors.

## 7. Weapon quality
- [ ] Weapons are original detailed Blender-authored models.
- [ ] Receiver, barrel, sights, magazine, controls and stock/grip read as separate manufactured components.
- [ ] Materials distinguish metal, polymer, rubber and glass.
- [ ] Weapon is correctly held by the character.
- [ ] Muzzle flash, impact feedback and reload animation are synchronized.

## 8. Performance
- [ ] 720p landscape target render/output is verified.
- [ ] 30 FPS gameplay target is tested.
- [ ] Low-quality profile is tested on constrained hardware/emulation.
- [ ] Balanced profile is stable.
- [ ] High profile is stable on the reference desktop.
- [ ] No runaway memory growth during a 20-minute match.
- [ ] Loading does not freeze the UI.
- [ ] Large map does not cause catastrophic frame-time spikes.

## 9. Automated acceptance
- [ ] Script/static scan finds no portrait orientation configuration.
- [ ] Static scan finds no legacy fixed movement buttons.
- [ ] Static scan confirms landscape 1280x720.
- [ ] Asset audit confirms required GLB/scene/character/weapon files.
- [ ] Map audit confirms collision proxy count >= 25.
- [ ] Map audit confirms >= 3 major buildings and >= 20 cover elements.
- [ ] Build audit records package size.
- [ ] Smoke test launches the game and exits cleanly.
- [ ] Final artifact checksum is recorded.

## 10. 590 MB quality floor
The 590 MB requirement is treated as an **asset-package quality floor**, not an excuse to add meaningless padding.
- [ ] Final package is >= 590 MB only after real high-resolution assets, animation data, audio, materials and map content are present.
- [ ] If below 590 MB, the build fails the packaging gate and must receive genuine missing content/quality assets rather than dummy padding.
- [ ] If the game is smaller because compression is appropriate, the asset-quality audit must explicitly prove all visual-quality gates still pass.

## 11. Daily completion procedure
Every daily run must:
1. Inspect current branch and latest commit.
2. Run the static acceptance checklist.
3. Build the Android/Desktop targets.
4. Run the movement/combat/UI smoke test.
5. Render the 1280x720 map preview.
6. Inspect the build logs for new errors.
7. Compare against this checklist.
8. Fix the highest-priority failing blocker automatically when possible.
9. Re-run the failed gate.
10. Never mark the prototype complete while a blocking gate remains unchecked.
11. Record the exact failing gate, attempted fix, commit SHA and resulting build status.
12. Continue on the next daily check until every blocking gate passes.

## Definition of DONE
DONE means **all blocking checks pass on the same commit**, the Android package launches, the player physically moves through the map, combat works, settings work, the world is detailed and navigable, and the final acceptance report contains no unresolved blocker.
