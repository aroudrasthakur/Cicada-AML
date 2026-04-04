"""Tests that training scripts are importable and have expected structure."""
import sys
import types
import pytest
import importlib
from unittest.mock import MagicMock

TRAINING_MODULES = [
    "app.ml.training.train_behavioral",
    "app.ml.training.train_graph",
    "app.ml.training.train_entity",
    "app.ml.training.train_temporal",
    "app.ml.training.train_document",
    "app.ml.training.train_offramp",
    "app.ml.training.train_meta",
]

# Stub optional heavy dependencies so import-only tests don't fail
_OPTIONAL_STUBS = {
    "xgboost": ["XGBClassifier"],
    "sklearn.calibration": ["CalibratedClassifierCV"],
}

for _mod_name, _attrs in _OPTIONAL_STUBS.items():
    if _mod_name not in sys.modules:
        _fake = types.ModuleType(_mod_name)
        for _a in _attrs:
            setattr(_fake, _a, MagicMock())
        sys.modules[_mod_name] = _fake


class TestTrainingScriptsExist:
    @pytest.mark.parametrize("module_path", TRAINING_MODULES)
    def test_importable(self, module_path):
        mod = importlib.import_module(module_path)
        assert mod is not None


class TestTrainingModuleStructure:
    @pytest.mark.parametrize("module_path", TRAINING_MODULES)
    def test_has_main_function(self, module_path):
        mod = importlib.import_module(module_path)
        assert hasattr(mod, "main"), f"{module_path} is missing main()"
        assert callable(mod.main)

    @pytest.mark.parametrize("module_path", TRAINING_MODULES)
    def test_has_output_dir(self, module_path):
        mod = importlib.import_module(module_path)
        assert hasattr(mod, "OUTPUT_DIR"), f"{module_path} is missing OUTPUT_DIR"
