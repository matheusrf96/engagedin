from __future__ import annotations

import runpy
import sys
from unittest.mock import patch

import pytest

from cli.__main__ import cli


def test_main_entry_point() -> None:
    with (
        patch.object(sys, "argv", ["engagedin", "--help"]),
        pytest.raises(SystemExit),
    ):
        runpy.run_module("cli", run_name="__main__")


def test_main_import() -> None:
    assert cli is not None
