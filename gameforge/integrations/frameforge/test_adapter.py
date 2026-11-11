import unittest
from adapter import to_runtime_timeline, validate_manifest

class FrameForgeAdapterTests(unittest.TestCase):
    def setUp(self):
        self.manifest={"manifest_version":"1.0","cinematic_id":"intro","duration_seconds":5,
          "shots":[{"shot_id":"wide","start":0,"duration":5,"camera":{"position":[0,2,5],"rotation":[0,0,0],"fov":55}}],
          "cues":[{"cue_id":"line1","kind":"dialogue","start":1,"duration":2,"speaker":"Mara","text":"We need to leave."},
                  {"cue_id":"subtitle1","kind":"subtitle","start":1,"duration":2,"text":"We need to leave."}]}
    def test_timeline_is_sorted(self):
        timeline=to_runtime_timeline(self.manifest)
        self.assertEqual(timeline["events"][0]["at"],1)
        self.assertEqual(len(timeline["events"]),2)
    def test_rejects_out_of_bounds_cue(self):
        self.manifest["cues"][0]["start"]=4
        with self.assertRaises(ValueError): validate_manifest(self.manifest)
    def test_rejects_duplicate_cue_ids(self):
        self.manifest["cues"][1]["cue_id"]="line1"
        with self.assertRaises(ValueError): validate_manifest(self.manifest)

if __name__=="__main__": unittest.main()
