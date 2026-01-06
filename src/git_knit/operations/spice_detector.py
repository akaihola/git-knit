"""Git-spice detection and integration."""

import subprocess
from typing import Literal


class GitSpiceDetector:
    """Detect if git-spice is available (not GhostScript)."""

    def detect(self) -> Literal["git-spice", "ghostscript", "not-found", "unknown"]:
        """Detect gs binary type."""
        try:
            # git-spice uses 'gs' as its binary name.
            # We check --help output to distinguish from GhostScript.
            result = subprocess.run(
                ["gs", "--help"], capture_output=True, text=True, check=False
            )
            output = (result.stdout or "") + (result.stderr or "")
            out = output.lower()
            if "git-spice" in out:
                return "git-spice"
            if "ghostscript" in out:
                return "ghostscript"
            return "unknown"
        except FileNotFoundError:
            return "not-found"

    def restack_if_available(self) -> bool:
        if self.detect() == "git-spice":
            try:
                subprocess.run(["gs", "stack", "restack"], check=True)
                return True
            except subprocess.CalledProcessError:
                return False
        return False
