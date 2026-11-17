"""Board Extractor: card records in, the Board Generator's board file and card file out.

    from board_extractor import board_file, card_file, ExtractorError

    text = board_file(settings, records, today="2026-03-10")
    text = card_file(settings, record)

See docs/guide.md. MIT licence.
"""

from .extract import ExtractorError, board_file, card_file, MAX_RECORDS

__version__ = "1.0.0"
__all__ = ["board_file", "card_file", "ExtractorError", "MAX_RECORDS", "__version__"]
