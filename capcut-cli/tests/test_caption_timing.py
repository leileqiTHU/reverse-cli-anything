"""Real 30 fps subtitle regression: 7,266,667 us saves as 7,266,666 us."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from capcut_extensions import caption_timing_matches

class CaptionTimingTests(unittest.TestCase):
    cue={'startUs':7266667,'endUs':8266667}

    def test_observed_native_fractional_frame_rounding(self):
        self.assertTrue(caption_timing_matches({'start':7266666,'duration':1000000},self.cue))

    def test_exact_and_one_microsecond_duration_rounding(self):
        self.assertTrue(caption_timing_matches({'start':7266667,'duration':1000000},self.cue))
        self.assertTrue(caption_timing_matches({'start':7266667,'duration':999999},self.cue))

    def test_rejects_real_drift_or_bad_state(self):
        for value in ({'start':7266665,'duration':1000000},{'start':7266667,'duration':999998},
                      {'start':7300000,'duration':1000000},{'start':7266667.0,'duration':1000000},
                      {'duration':1000000}):
            self.assertFalse(caption_timing_matches(value,self.cue),value)

if __name__=='__main__':
    unittest.main()
