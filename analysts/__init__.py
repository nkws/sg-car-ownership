"""Registry of thought leaders.

To add a new analyst:
  1. Create `analysts/<name>_mock.py` (or real-data module) exporting an
     `Analyst` dict.
  2. Import it below and add one entry to ANALYSTS.
"""

from models.analyst import Analyst

from .bremmer_mock import BREMMER
from .burry_mock import BURRY
from .eisman_mock import EISMAN
from .galloway_mock import GALLOWAY

ANALYSTS: dict[str, Analyst] = {
    BREMMER["id"]: BREMMER,
    GALLOWAY["id"]: GALLOWAY,
    BURRY["id"]: BURRY,
    EISMAN["id"]: EISMAN,
}
