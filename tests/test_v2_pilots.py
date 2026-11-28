from __future__ import annotations
import json, subprocess, sys, tempfile, unittest, wave
from pathlib import Path
from PIL import ImageChops
from tools.render_v2_pilots import DURATION, FPS, PILOTS, ROOT, create_sfx, render_frame

class V2PilotTests(unittest.TestCase):
    def test_projects_manifests_and_original_assets_validate(self):
        for key, details in PILOTS.items():
            folder=ROOT/"projects"/"v2-pilots"/details["folder"]
            for script,path in (("validate_project.py",folder/"project.json"),("validate_media_manifest.py",folder/"media_manifest.json")):
                result=subprocess.run([sys.executable,str(ROOT/"tools"/script),str(path)],cwd=ROOT,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            project=json.loads((folder/"project.json").read_text(encoding="utf-8"))
            self.assertEqual(project["sequences"][0]["duration_frames"],DURATION*FPS)
            self.assertGreaterEqual(len(project["sequences"][0]["tracks"]),5)
            for asset in project["assets"]:
                self.assertEqual(asset["provenance"]["source_type"],"procedural")
                self.assertEqual(asset["rights"]["status"],"approved")
                self.assertTrue((folder/asset["uri"]).is_file())
    def test_distinct_motion_treatments(self):
        power_a=render_frame("entertainment",20,320,180)
        power_b=render_frame("entertainment",100,320,180)
        cyber_a=render_frame("cybersecurity",20,320,180)
        cyber_b=render_frame("cybersecurity",100,320,180)
        self.assertIsNotNone(ImageChops.difference(power_a,power_b).getbbox())
        self.assertIsNotNone(ImageChops.difference(cyber_a,cyber_b).getbbox())
        self.assertIsNotNone(ImageChops.difference(power_a,cyber_a).getbbox())
    def test_sfx_pcm_shape_and_safe_peak(self):
        with tempfile.TemporaryDirectory() as folder:
            for pilot in PILOTS:
                path=Path(folder)/(pilot+".wav")
                report=create_sfx(path,pilot)
                with wave.open(str(path),"rb") as wav:
                    self.assertEqual((wav.getnchannels(),wav.getframerate(),wav.getnframes(),wav.getsampwidth()),(2,48000,12*48000,2))
                self.assertGreater(report["peak_linear"],0.01)
                self.assertLessEqual(report["peak_linear"],0.24)

if __name__=="__main__": unittest.main()
