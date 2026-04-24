import logging
import subprocess
import time

logger = logging.getLogger("timing")


def get_vram_mb() -> str:
    """Current GPU memory usage in MB (from nvidia-smi)."""
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,nounits,noheader"],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip().replace("\n", " / ") + " MB"
    except Exception:
        return "N/A"


class Timer:
    """Context manager that logs elapsed time and VRAM when DEBUG_TIMING is on.

    Usage:
        with Timer("model loading"):
            session = rt.InferenceSession(...)
    """

    def __init__(self, label: str):
        self.label = label
        self.start: float = 0

    def __enter__(self):
        from app.config import settings
        if settings.DEBUG_TIMING:
            self.start = time.time()
            logger.info(f"[TIMING] {self.label} START | VRAM: {get_vram_mb()}")
        return self

    def __exit__(self, *args):
        from app.config import settings
        if settings.DEBUG_TIMING:
            ms = (time.time() - self.start) * 1000
            logger.info(f"[TIMING] {self.label} DONE | {ms:.0f} ms | VRAM: {get_vram_mb()}")
