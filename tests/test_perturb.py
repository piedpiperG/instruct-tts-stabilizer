import unittest

from instruct_tts_stabilizer.perturb.audio import atempo_chain, build_ffmpeg_filter


class PerturbTests(unittest.TestCase):
    def test_atempo_chain_bounds(self):
        chain = atempo_chain(4.0)
        self.assertEqual(chain, ["atempo=2.00000000", "atempo=2.00000000"])

    def test_filter_contains_volume(self):
        filt = build_ffmpeg_filter(volume_db=3)
        self.assertIn("volume=3dB", filt)


if __name__ == "__main__":
    unittest.main()

