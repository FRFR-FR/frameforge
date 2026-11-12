# Kyutai voice catalogue and usage note

GAMEFORGE only accepts the following predefined English Pocket TTS voice identifiers:

| UI label | Canonical Pocket TTS ID |
|---|---|
| Eponine | `eponine` |
| George | `george` |
| Ezelma | `azelma` |
| Bill Boerst | `bill_boerst` |
| Jean | `jean` |
| Michael | `michael` |
| Peter Yearsley | `peter_yearsley` |
| Stuart Bell | `stuart_bell` |
| Charles | `charles` |

Kyutai's official Pocket TTS documentation lists these voice IDs as available English voices. Its public voice repository contains several source datasets under different terms (including CC0, CC BY 4.0 and CC BY-NC 4.0). The exact license must be checked for each selected voice/source before using the generated dialogue in a commercial release. Do not assume every preset voice shares one blanket license.

Official references:
- https://github.com/kyutai-labs/pocket-tts
- https://huggingface.co/kyutai/tts-voices

The model can generate audio from predefined voices using its Python API. GAMEFORGE does not allow arbitrary cloned voices or user-supplied voice prompts in this configuration.
