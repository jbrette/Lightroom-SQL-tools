# -*- coding: utf-8 -*-
# pylint: disable=invalid-name

"""

Configuration for LRTool

"""

import sys
import os
from configparser import ConfigParser

# sections
CONFIG_MAIN = "Main"


class LRConfigException(Exception):
    """lrtools config exception"""


class LRToolConfig:
    """
    Singleton class for LRTools config
    """

    def __init__(self, config_filename="lrtools.ini"):
        """load default config

            If config_filename has a full path, it will be used.
            If it only has a filename, it will be searched for in the current
            directory, the directory the script is stored, then ~/.config/lrtools.
            If it is None, defaults will be used.
        """
        self.default_lrcat = (
            "C:\\Users\\Default\\Documents\\My Lightroom Catalog.lrcat"
        )
        self.dayfirst = True
        self.geocoder = "nominatim"

        # no config file found: silently use defaults
        if config_filename and os.path.isfile(self.find(config_filename)):
            try:
                self.load(config_filename)
            except LRConfigException:
                print(
                    "WARNING: failed to read config file",
                    config_filename,
                    file=sys.stderr,
                )

    @staticmethod
    def find(filename):
        """
        return config file path : filename itself if it has a directory part, else
        first existing in current directory, script directory, then user config directory
        """
        _dir, _ = os.path.split(filename)
        if _dir:
            return filename
        candidates = [
            os.path.join(os.getcwd(), filename),
            os.path.join(os.path.dirname(sys.argv[0]), filename),
            os.path.join(os.path.expanduser("~"), ".config", "lrtools", filename),
        ]
        return next((_f for _f in candidates if os.path.isfile(_f)), candidates[0])

    def load(self, filename):
        """load a config file"""

        # parser and default value
        parser = ConfigParser(
            {
                "LRCatalog": self.default_lrcat,
                "DayFirst": self.dayfirst,
                "GeoCoder": self.geocoder,
            }
        )

        try:
            parser.read(self.find(filename))
            self.default_lrcat = parser.get(CONFIG_MAIN, "LRCatalog")
            self.dayfirst = parser.getboolean(CONFIG_MAIN, "DayFirst")
            self.geocoder = parser.get(CONFIG_MAIN, "GeoCoder")

        except Exception as _e:
            raise LRConfigException(
                f'Failed to read config file "{filename}"'
            ) from _e
