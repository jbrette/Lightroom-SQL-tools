"""Configuration for LRTool."""

import sys
from configparser import ConfigParser
from pathlib import Path

# sections
CONFIG_MAIN = "Main"


class LRConfigException(Exception):  # noqa: N818 public API name
    """Lrtools config exception."""


class LRToolConfig:
    """Singleton class for LRTools config."""

    def __init__(self, config_filename: str | None = "lrtools.ini") -> None:
        """Load default config.

        If config_filename has a full path, it will be used.
        If it only has a filename, it will be searched for in the current
        directory, the directory the script is stored, then ~/.config/lrtools.
        If it is None, defaults will be used.
        """
        self.default_lrcat = "C:\\Users\\Default\\Documents\\My Lightroom Catalog.lrcat"
        self.dayfirst = True
        self.geocoder = "nominatim"

        # no config file found: silently use defaults
        if config_filename and Path(self.find(config_filename)).is_file():
            try:
                self.load(config_filename)
            except LRConfigException:
                sys.stderr.write(f"WARNING: failed to read config file {config_filename}\n")

    @staticmethod
    def find(filename: str) -> str:
        """Return config file path.

        The path is filename itself if it has a directory part, else the first existing
        in current directory, script directory, then user config directory.
        """
        if Path(filename).name != filename:
            return filename
        candidates = [
            Path.cwd() / filename,
            Path(sys.argv[0]).parent / filename,
            Path.home() / ".config" / "lrtools" / filename,
        ]
        return str(next((_f for _f in candidates if _f.is_file()), candidates[0]))

    def load(self, filename: str) -> None:
        """Load a config file."""
        # parser and default value
        parser = ConfigParser(
            {
                "LRCatalog": self.default_lrcat,
                "DayFirst": str(self.dayfirst),
                "GeoCoder": self.geocoder,
            }
        )

        try:
            parser.read(self.find(filename))
            self.default_lrcat = parser.get(CONFIG_MAIN, "LRCatalog")
            self.dayfirst = parser.getboolean(CONFIG_MAIN, "DayFirst")
            self.geocoder = parser.get(CONFIG_MAIN, "GeoCoder")

        except Exception as _e:
            msg = f'Failed to read config file "{filename}"'
            raise LRConfigException(msg) from _e
