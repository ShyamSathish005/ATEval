import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ateval.revisions import human_evaluation


class HumanEvaluationTests(unittest.TestCase):
    def test_public_packet_hides_candidate_identity_and_randomizes_by_reviewer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet = root / "packet.jsonl"
            key = root / "key.json"
            packet.write_text(json.dumps({
                "item_id": "item-1", "kind": "comparison", "original_text": "source",
                "candidate_count": 3, "candidate_ids_available": ["ORIGINAL", "FULL_MODEL", "SCAR_CANDIDATE", "HUMAN_REFERENCE"],
            }) + "\n")
            key.write_text(json.dumps({"key": {"item-1": {
                "ORIGINAL": "source", "FULL_MODEL": "full", "SCAR_CANDIDATE": "scar", "HUMAN_REFERENCE": "human",
            }}}))
            with patch.object(human_evaluation, "PACKET_PATH", packet), patch.object(human_evaluation, "KEY_PATH", key):
                first = human_evaluation.public_packet("reviewer-a")
                second = human_evaluation.public_packet("reviewer-b")
            self.assertTrue(first[0]["candidates"])
            self.assertNotIn("candidate_id", str(first))
            self.assertNotIn("candidate_ids_available", str(first))
            self.assertNotIn("FULL_MODEL", str(first))
            self.assertNotEqual(first[0]["candidates"], second[0]["candidates"])

    def test_annotation_schema_rejects_invalid_confidence_and_accepts_abstention(self):
        valid = {
            "item_id": "item-1", "reviewer_id": "r1",
            "editing_necessity": "INSUFFICIENT_CONTEXT", "confidence": 1,
            "candidate_assessments": [], "abstained": True,
        }
        human_evaluation.validate_annotation(valid)
        with self.assertRaises(ValueError):
            human_evaluation.validate_annotation({**valid, "confidence": 6})


if __name__ == "__main__":
    unittest.main()
