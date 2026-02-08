"""Tests for settings persistence."""

import json
import os
import tempfile
import unittest

from gate_horizons.game.settings import GameSettings, SettingsManager


class TestSettingsManager(unittest.TestCase):
    def test_load_defaults_when_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "settings.json")
            manager = SettingsManager(path)
            settings = manager.load()
            self.assertEqual(settings.music_volume, 0.7)
            self.assertEqual(settings.sfx_volume, 0.7)
            self.assertTrue(settings.autosave_enabled)

    def test_save_and_reload(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "settings.json")
            manager = SettingsManager(path)
            settings = GameSettings(music_volume=0.2, sfx_volume=0.4, autosave_enabled=False)
            manager.save(settings)
            loaded = manager.load()
            self.assertAlmostEqual(loaded.music_volume, 0.2, places=2)
            self.assertAlmostEqual(loaded.sfx_volume, 0.4, places=2)
            self.assertFalse(loaded.autosave_enabled)

    def test_clamps_invalid_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "settings.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(
                    {"music_volume": 2.5, "sfx_volume": -1, "autosave_enabled": "yes"},
                    handle,
                )
            manager = SettingsManager(path)
            loaded = manager.load()
            self.assertEqual(loaded.music_volume, 1.0)
            self.assertEqual(loaded.sfx_volume, 0.0)
            self.assertTrue(loaded.autosave_enabled)
