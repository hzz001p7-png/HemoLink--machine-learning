"""Módulo de Machine Learning do HemoLink para matching de doadores de sangue."""

import os
import tempfile
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "hemolink_mpl"))
