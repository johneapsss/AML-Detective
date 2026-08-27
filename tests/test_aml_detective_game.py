import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aml_detective_game import load_game_content, play_game


class AMLDetectiveGameTests(unittest.TestCase):
    def test_load_game_content_from_json_document(self):
        payload = {
            "title": "Test Title",
            "intro": "Intro",
            "cases": [
                {
                    "id": "c1",
                    "title": "Case",
                    "scenario": "Scenario",
                    "choices": [
                        {
                            "key": "a",
                            "text": "Do thing",
                            "is_correct": True,
                            "explanation": "Nice"
                        }
                    ],
                    "success_summary": "ok",
                    "failure_summary": "no"
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "content.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            content = load_game_content(path)

        self.assertEqual(content.title, "Test Title")
        self.assertEqual(len(content.cases), 1)
        self.assertEqual(content.cases[0].choices[0].key, "A")

    def test_play_game_scores_correct_choice(self):
        content = load_game_content(
            Path(__file__).resolve().parents[1] / "game_content.json"
        )

        with patch("builtins.input", side_effect=["a", "a"]):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                score = play_game(content)

        self.assertEqual(score, 2)
        self.assertIn("Final score: 2/2", mock_stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
