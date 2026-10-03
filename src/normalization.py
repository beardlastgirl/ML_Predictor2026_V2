"""Canonical name normalization utilities."""

import re
import pandas as pd

_ACCENT_MAP = str.maketrans({"A": "A", "E": "E", "I": "I", "O": "O", "U": "U",
                              "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U", "Ü": "U", "Ñ": "N"})


def canonicalize_name(name) -> str:
    """Normalize a raw string into canonical uppercase form for matching.

    Strips whitespace, uppercases, removes accents, drops dots, converts
    hyphens/dashes to spaces, and collapses repeated whitespace.
    """
    if name is None:
        return ""
    try:
        if pd.isna(name):
            return ""
    except (TypeError, ValueError):
        pass

    name = str(name).strip().upper()
    name = name.replace(".", "").replace("-", " ").replace("–", " ").replace("—", " ")
    name = name.translate(_ACCENT_MAP)
    name = re.sub(r"\s+", " ", name).strip()
    return name
