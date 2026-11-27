# EP002 narration — The Machine That Prints the World's Most Advanced Chips

Channel: Underneath Everything
Target export: 1280×720, 16:9, H.264 + AAC
Voice: Kokoro-82M, American English Echo (am_echo)
Captions: none

## 01 — The flash that helps build a chip

Inside one of the most complicated machines on Earth, a laser fires at a droplet of molten tin. A second pulse hits it, turning the metal into plasma that emits an extraordinary kind of light. That process repeats tens of thousands of times every second. It is not a science-fiction weapon. It is part of the process used to manufacture some of the world's most advanced microchips.

The light has a wavelength of just 13.5 nanometres. It travels through a system of precision mirrors while a silicon wafer and a patterned mask move in carefully coordinated motion. The wafer's position is checked and corrected thousands of times per second.

This is extreme ultraviolet lithography, or EUV. It helps print some of the most intricate patterns in leading-edge processors. But the machine does not print a complete chip in one go. To see why it is so difficult to build, follow one tiny pattern from a design to a piece of silicon.

## 02 — A chip is a city built in layers

A modern processor may look like a small, flat square. Inside, it is a three-dimensional landscape of electrical structures connected through many layers. It is not made by stamping one complete picture onto a wafer. It is built through a long sequence of manufacturing steps.

A polished silicon wafer travels through a highly controlled factory. Robots move it between machines. Materials are added, surfaces are prepared, patterns are exposed, selected areas are etched, and measurements check each stage. The cycle repeats. ASML says modern chips can contain up to one hundred layers, and manufacturing involves hundreds of steps. The total varies by design.

Each new pattern must align precisely with the layers below it. Engineers call this overlay.

Lithography transfers a pattern onto a light-sensitive coating on the wafer. EUV scanners are designed to print some of the smallest and most demanding patterns in that stack.

## 03 — Why the industry needed a different kind of light

Chipmakers have long used ultraviolet light to project patterns onto silicon. As designs became more demanding, shorter wavelengths helped print smaller features. Deep ultraviolet, or DUV, remains essential; one widely used DUV wavelength is 193 nanometres.

EUV takes a much bigger leap. Its wavelength is 13.5 nanometres—more than fourteen times shorter than 193 nanometres. That does not mean a chip advertised as a “three-nanometre” or “two-nanometre” product contains features exactly three or two nanometres wide. Node names are generation labels, not a simple measurement of every transistor feature.

The practical advantage is that EUV can print some intricate layers with fewer complicated patterning steps than would otherwise be needed. It does not replace every other lithography tool. EUV and DUV work alongside one another because different layers have different requirements.

Making 13.5-nanometre light is not like changing a bulb: air absorbs it, and the source begins with liquid metal.

## 04 — Turning a tin droplet into a flash of light

The light source fires tiny droplets of molten tin into a chamber. ASML describes droplets around twenty-five micrometres in diameter travelling at about seventy metres per second. Each droplet is struck by two laser pulses. The first reshapes it into a flatter target. The second delivers much more energy and turns the tin into plasma. As that plasma cools, it emits extreme ultraviolet radiation.

The process can repeat up to fifty thousand times per second. The challenge is producing stable, repeatable flashes while controlling timing, direction and debris around the source.

A real scanner's source is enclosed and highly engineered; the 3D sequence in this film is an original explanation of the principle, not a recording of a proprietary machine interior.

## 05 — Why the machine uses mirrors and a vacuum

EUV light is absorbed by ordinary materials, including air and glass. That makes a conventional lens system unsuitable. The light travels through a high-vacuum path, and carefully designed mirrors guide it from the source toward the wafer.

These are not everyday mirrors. Their surfaces use many extremely thin alternating layers. The layers are engineered so reflections reinforce one another at the required wavelength. ZEISS, an optics supplier to the EUV ecosystem, describes molybdenum-and-silicon multilayer coatings that can reflect up to about seventy percent of the EUV light that reaches them.

Every reflection costs light, so the optical path must be carefully designed and the source must produce enough usable radiation for the wafer.

Cleanliness is critical: particles can interfere with the optics or wafer process, so vacuum and contamination control matter as much as mirror precision.

## 06 — From a pattern on a mask to a pattern on silicon

The pattern begins on a component called a reticle. Think of it as an engineered mask carrying the circuit pattern for one exposure. In EUV systems, the reticle is reflective because the light cannot pass through an ordinary transparent mask as visible light passes through a slide.

The optical system directs light from the reticle toward the wafer and reduces the pattern. ASML describes its EUV optical column as shrinking the reticle pattern by a factor of four. The wafer is coated with photoresist, a material whose chemistry changes when exposed to light.

After exposure, a developer removes selected portions of the resist, leaving a temporary pattern. That pattern can guide an etch or another material-processing step. The resist is not the finished transistor. It is a temporary mask that helps shape the layers underneath.

It is a photographic stencil at nanometre-scale precision: one accurately placed pattern in a much larger structure.

## 07 — The wafer stage: precision while in motion

The wafer cannot simply sit still while the pattern is projected across the exposure field. The system scans, moving the reticle and wafer in coordinated motion. Their movement has to stay synchronized as the machine accelerates, decelerates and measures position.

ASML says its wafer stage can position a wafer to within a quarter of a nanometre for an exposure, with its position checked and adjusted twenty thousand times per second. That is a manufacturer specification for its system, not a claim that every component in the factory is held to the same tolerance.

Sensors, precision mechanics and active correction work together. The machine continually measures where the wafer is and adjusts its position. The goal is not simply to move quickly. It is to move quickly and still place each exposure where the design expects it.

Source, optics and stage must work together to place each exposure correctly.

## 08 — Repeating the process without losing alignment

After one layer has been patterned and processed, the wafer returns for more steps. New materials are deposited. A fresh coating is applied. Another pattern is aligned and exposed. More material is etched, cleaned or measured. Layer by layer, the circuit grows into a three-dimensional structure.

It is misleading to say that one EUV machine makes an entire processor. ASML says EUV is used for the most intricate layers, while DUV systems print other layers with larger or less demanding features. The exact mix depends on the chip design and manufacturing process.

Every new pattern must align with the underlying layers. Misplaced connections can affect the circuit, so the factory measures the process repeatedly.

The scanner is part of a larger production line that includes material deposition, etch, cleaning, inspection, metrology and process control. The final chip is the result of that whole system.

## 09 — High-NA: the next step is entering production

The EUV machines widely used in leading-edge manufacturing have a numerical aperture, or NA, of 0.33. A newer generation called High-NA raises that figure to 0.55. Numerical aperture describes how the optical system gathers and focuses light. In lithography, increasing it can improve resolution and help print smaller patterns.

ASML lists an eight-nanometre resolution specification for its first High-NA system, the EXE:5000. The company says it can print features about 1.7 times smaller in a single exposure than its NXE systems, with a theoretical transistor-density comparison of 2.9 times. Those are vendor specifications, not a guarantee that every customer design becomes 2.9 times denser. They are also not a conversion from tool resolution to a chip's node name.

There is now a real production milestone. In July 2026, ASML announced that Intel Foundry had begun high-volume manufacturing for a subset of Core Ultra Series 3 processors using High-NA EUV on selected Intel 18A layers. In September, ASML and Intel said more than one million wafers had been processed across early tool certification and testing, research and development, and production on selected layers for that subset of products.

The milestone does not mean one million finished chips were made with High-NA, or that every layer used it. High-volume manufacturing has begun on selected layers, while broader adoption still requires qualification.

## 10 — The machine is only one part of the breakthrough

The scanner is extraordinary, but no single component builds a chip. Its light source, lasers, optics, motion systems, sensors, software, photoresist, masks and wafer processes must work together.

That is the story underneath the processor in a phone, a laptop or an artificial-intelligence system. A tiny pattern is not printed by a tiny machine. It is printed by a factory-scale system that turns molten metal into light, sends that light across precision mirrors, and moves silicon with astonishing control.

Exposure is only one step in the hundreds required to finish a chip.

The next time you hold a device in your hand, remember that its processor began as a design, became a set of patterns, and was built layer by layer through a process that makes light itself part of the manufacturing tool.