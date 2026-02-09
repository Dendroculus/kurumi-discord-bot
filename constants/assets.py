import logging
from typing import Optional
from constants.configs import ASSETS_DIR, GIF_ASSETS

class AssetService:
    """
    Service responsible for loading and managing binary assets.

    Responsibilities:
    - Preloads GIF assets from the configured directory.
    - Provides access to raw asset bytes by key.
    """

    def __init__(self):
        self.logger = logging.getLogger("bot")
        self.gifs: dict[str, bytes] = {}
        self._preload_assets()

    def _preload_assets(self) -> None:
        """
        Load configured asset files into memory.

        Looks up file names relative to config.ASSETS_DIR. Missing assets are logged
        at WARNING level; unexpected errors during load are logged at ERROR level.
        """
        base_path = ASSETS_DIR
        files = {
            "info": GIF_ASSETS["Kurumi"],
            "welcome": GIF_ASSETS["Kurumi_1"],
            "mention": GIF_ASSETS["Kurumi_2"],
            "dm": GIF_ASSETS["Kurumi_3"],
        }
        for key, fname in files.items():
            path = base_path / fname
            try:
                with open(path, "rb") as f:
                    self.gifs[key] = f.read()
            except FileNotFoundError:
                self.logger.warning("Asset missing: %s (key=%s)", path, key)
            except Exception as e:
                self.logger.exception("Error loading asset %s: %s", path, e)

    def get_asset(self, key: str) -> Optional[bytes]:
        """
        Retrieve the raw bytes for a named asset.

        Args:
            key: The key of the asset to retrieve (e.g., "welcome", "mention").

        Returns:
            Optional[bytes]: The asset bytes if found, None otherwise.
        """
        return self.gifs.get(key)