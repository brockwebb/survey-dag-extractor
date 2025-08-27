# utils/silence.py
from __future__ import annotations
import contextlib, io, logging, os

@contextlib.contextmanager
def mute_everything():
    prev_disable = logging.root.manager.disable
    prev_absl = None
    try:
        logging.disable(logging.CRITICAL)
        try:
            from absl import logging as absl_logging
            prev_absl = absl_logging.get_verbosity()
            absl_logging.set_verbosity(absl_logging.FATAL)
            os.environ["ABSL_LOGGING_MIN_SEVERITY"] = "3"
        except Exception:
            pass
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            yield
    finally:
        logging.disable(prev_disable)
        if prev_absl is not None:
            from absl import logging as absl_logging
            absl_logging.set_verbosity(prev_absl)

