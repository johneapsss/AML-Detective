import io
import json
import tempfile
import unittest
from pathlib import Path

from aml_detective_game import load_game_content, play_game


class AMLDetectiveGameTests(unittest.TestCase):
    def test_web_assets_exist_and_are_wired(self):
        repo_root = Path(__file__).resolve().parents[1]
        index_html = repo_root / "index.html"
        style_css = repo_root / "style.css"
        game_js = repo_root / "game.js"

        self.assertTrue(index_html.exists())
        self.assertTrue(style_css.exists())
        self.assertTrue(game_js.exists())

        html_content = index_html.read_text(encoding="utf-8")
        js_content = game_js.read_text(encoding="utf-8")
        self.assertIn('href="style.css"', html_content)
        self.assertIn('src="game.js"', html_content)
        self.assertIn('fetch("game_content.json")', js_content)

    def test_load_game_content_from_requirements_document(self):
        content = load_game_content(
            Path(__file__).resolve().parents[1] / "game_content.json"
        )

        self.assertEqual(len(content.cases), 3)
        self.assertEqual(content.cases[0].difficulty, "easy")
        self.assertEqual(content.cases[1].difficulty, "intermediate")
        self.assertEqual(content.cases[2].difficulty, "advanced")
        self.assertIn("time", content.starting_resources)
        self.assertGreaterEqual(len(content.cases[0].evidence), 4)

    def test_play_game_awards_xp_and_persists_progress(self):
        content = load_game_content(
            Path(__file__).resolve().parents[1] / "game_content.json"
        )

        # Case 1: take all actions, submit correct conclusion, then stop.
        inputs = iter(["A", "B", "C", "S", "A", "N"])

        def fake_input(prompt: str) -> str:
            return next(inputs)

        with tempfile.TemporaryDirectory() as tmp_dir:
            save_file = Path(tmp_dir) / "progress.json"
            with io.StringIO() as _:
                summary = play_game(
                    content=content,
                    save_file=save_file,
                    progress=None,
                    input_fn=fake_input,
                    output_fn=lambda _msg: None,
                )

            saved = json.loads(save_file.read_text(encoding="utf-8"))

        self.assertEqual(summary["current_case_index"], 1)
        self.assertEqual(saved["profile"]["experience"], 5)
        self.assertEqual(saved["profile"]["capacity"]["time"], 105)
        self.assertTrue(saved["case_history"][0]["solved"])

    def test_free_text_action_is_interpreted(self):
        content = load_game_content(
            Path(__file__).resolve().parents[1] / "game_content.json"
        )

        # Use free text to map to transaction review action in case 1.
        inputs = iter(["F", "review transactions and chains", "S", "A", "N"])

        def fake_input(prompt: str) -> str:
            return next(inputs)

        with tempfile.TemporaryDirectory() as tmp_dir:
            save_file = Path(tmp_dir) / "progress.json"
            summary = play_game(
                content=content,
                save_file=save_file,
                progress=None,
                input_fn=fake_input,
                output_fn=lambda _msg: None,
            )

        self.assertIn("B", summary["case_history"][0]["actions_taken"])


if __name__ == "__main__":
    unittest.main()
