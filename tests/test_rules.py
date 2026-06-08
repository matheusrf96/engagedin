from __future__ import annotations

from pathlib import Path

from engagedin.core.models import Tone
from engagedin.rules.loader import load_ruleset


class TestLoadRuleset:
    def test_load_defaults(self) -> None:
        ruleset = load_ruleset()
        assert ruleset.tone == Tone.professional
        assert 100 <= ruleset.min_length <= 500
        assert 2000 <= ruleset.max_length <= 5000
        assert 1 <= ruleset.hashtags.count <= 10

    def test_load_custom_file(self, tmp_path: Path) -> None:
        custom_yaml = tmp_path / "rules.yaml"
        custom_yaml.write_text(
            "tone: educational\nmin_length: 200\nmax_length: 1500\n"
        )
        ruleset = load_ruleset(custom_yaml)
        assert ruleset.tone == Tone.educational
        assert ruleset.min_length == 200
        assert ruleset.max_length == 1500

    def test_load_invalid_path_falls_back_to_defaults(self) -> None:
        ruleset = load_ruleset("/nonexistent/path/rules.yaml")
        assert ruleset.tone == Tone.professional
