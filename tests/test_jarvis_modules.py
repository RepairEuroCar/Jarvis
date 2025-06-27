import importlib

import jarvis
import modules.analyzer


def test_import_alias_for_analyzer():
    mod = importlib.import_module("jarvis.modules.analyzer")
    assert mod is modules.analyzer
