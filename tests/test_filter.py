import unittest

from instruct_tts_stabilizer.filter.drift import heuristic_score, parse_score
from instruct_tts_stabilizer.filter.apply_filter import should_keep


class FilterTests(unittest.TestCase):
    def test_parse_score(self):
        self.assertEqual(parse_score("8"), 8)
        self.assertEqual(parse_score("score: 10"), 10)

    def test_heuristic_catches_role_assumption(self):
        score, drift = heuristic_score("模仿导游", "您跟着我走，咱这就开讲！", ["导游"])
        self.assertLessEqual(score, 5)
        self.assertIn(drift, {"role_assumption", "entity_label"})

    def test_majority_vote_filter(self):
        keep, reason = should_keep({"score": 7, "scores": [8, 3, 4]}, threshold=5)
        self.assertFalse(keep)
        self.assertEqual(reason, "majority_score_le_5")


if __name__ == "__main__":
    unittest.main()

