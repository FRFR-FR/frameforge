#!/usr/bin/env python3
"""Bootstrap for the versioned GAMEFORGE Loomglass Blender generator.

The full implementation is stored alongside as a gzip/base64 payload so the
GitHub Contents API can commit it safely as UTF-8 text. This loader expands it
to a temporary Python source file and executes it in Blender.
"""
import base64
import gzip
from pathlib import Path
import runpy
import sys

payload_path = Path(__file__).with_name("build_character_test.py.gz.b64")
runtime_path = Path(__file__).with_name("_build_character_test_runtime.py")
source = gzip.decompress(base64.b64decode(payload_path.read_text(encoding="ascii")))
runtime_path.write_bytes(source)
try:
    runpy.run_path(str(runtime_path), run_name="__main__")
finally:
    try:
        runtime_path.unlink()
    except OSError:
        pass
