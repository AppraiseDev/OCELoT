"""
Project OCELoT: Open, Competitive Evaluation Leaderboard of Translations

Shared helpers for reading (optionally gzip-compressed) uploaded files.
"""
import os
import tempfile
from contextlib import contextmanager

from sacrebleu.utils import smart_open


@contextmanager
def open_uploaded_text(uploaded_file, suffix=''):
    """Yield a decompressed text stream for an uploaded file.

    Handles both Django upload backings transparently:

    * on-disk uploads (``temporary_file_path()``) are read in place;
    * in-memory uploads are spilled to a temporary file that is **always**
      removed afterwards (fixing a previous temp-file leak).

    ``smart_open`` provides transparent gzip decompression based on the file
    extension, so ``suffix`` should preserve the upload's extension (e.g.
    ``.jsonl.gz``) for the in-memory case. The uploaded file's read position is
    reset to the start before and after use.
    """
    uploaded_file.seek(0)
    created_path = None
    try:
        if hasattr(uploaded_file, 'temporary_file_path'):
            file_path = uploaded_file.temporary_file_path()
        else:
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=suffix
            ) as temp_file:
                temp_file.write(uploaded_file.read())
                file_path = temp_file.name
                created_path = file_path
        with smart_open(file_path, 'rt', encoding='utf-8') as stream:
            yield stream
    finally:
        if created_path is not None:
            try:
                os.unlink(created_path)
            except OSError:
                pass
        uploaded_file.seek(0)
