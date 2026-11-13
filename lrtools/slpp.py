"""Lua table parser, from an old version of project https://github.com/SirAnthony/slpp."""

import logging
import re
from typing import Any

log = logging.getLogger(__name__)

# A decoded Lua value. Table keys are left as Any: a Lua key can be any value.
type LuaValue = str | int | float | bool | list[LuaValue] | dict[Any, LuaValue] | None
type LuaTable = dict[Any, LuaValue]


class SLPP:
    """Decode Lua tables to Python values, and encode Python values to Lua tables."""

    def __init__(self) -> None:
        """Init an empty parser."""
        self.text = ""
        self.ch = ""
        self.at = 0
        self.len = 0
        self.depth = 0

    def decode(self, text: str | None) -> LuaValue:
        """Decode a Lua table source, None if empty or not a string."""
        if not text or not isinstance(text, str):
            return None
        text = re.sub("---.*$", "", text, flags=re.MULTILINE)
        self.text = text
        self.at, self.ch, self.depth = 0, "", 0
        self.len = len(text)
        self.next_chr()
        result = self.value()
        if not result:
            return None
        return result

    def encode(self, obj: object) -> str | None:
        """Encode a Python value to a Lua table source, None if obj is empty."""
        if not obj:
            return None
        self.depth = 0
        return self.__encode(obj)

    def __encode(self, obj: object) -> str:
        s = ""
        tab = "\t"
        newline = "\n"
        if isinstance(obj, str):
            s += '"' + obj + '"'
        elif isinstance(obj, bool):
            s += str(obj).lower()
        elif isinstance(obj, int | float | complex):
            s += str(obj)
        elif isinstance(obj, list | tuple):
            s += "{" + newline
            self.depth += 1
            for el in obj:
                s += tab * self.depth + self.__encode(el) + "," + newline
            self.depth -= 1
            s += tab * self.depth + "}"
        elif isinstance(obj, dict):
            s += "{" + newline
            self.depth += 1
            for key in obj:
                # Lua number keys are written as list items.
                if type(key) is int:
                    s += tab * self.depth + self.__encode(obj[key]) + "," + newline
                elif isinstance(key, str):
                    s += tab * self.depth + key + " = " + self.__encode(obj[key]) + "," + newline
                else:
                    msg = f"unsupported Lua table key: {key!r}"
                    raise TypeError(msg)
            self.depth -= 1
            s += tab * self.depth + "}"
        return s

    def white(self) -> None:
        """Skip spaces and tabs."""
        while self.ch:
            if self.ch in {" ", "\t"}:
                self.next_chr()
            else:
                break

    def next_chr(self) -> bool:
        """Move to the next character, False (and empty self.ch) at the end of text."""
        if self.at >= self.len:
            self.ch = ""
            return False
        self.ch = self.text[self.at]
        self.at += 1
        return True

    def value(self) -> LuaValue:
        """Parse any value."""
        self.white()
        if not self.ch:
            return None
        if self.ch == "{":
            return self.object()
        if self.ch == '"':
            return self.string()
        if self.ch.isdigit() or self.ch == "-":
            return self.number()
        return self.word()

    def string(self) -> str | None:
        """Parse a double-quoted string."""
        s = ""
        if self.ch == '"':
            while self.next_chr():
                if self.ch == '"':
                    self.next_chr()
                    return str(s)
                s += self.ch
        log.error("Unexpected end of string while parsing Lua string")
        return None

    def object(self) -> LuaTable | list[LuaValue] | None:
        """Parse a table: a list if it has no string key, a dict otherwise."""
        o: LuaTable = {}
        k: LuaValue = ""
        idx = 0
        self.depth += 1
        self.next_chr()
        self.white()
        if self.ch and self.ch == "}":
            self.depth -= 1
            self.next_chr()
            return o  # Exit here
        while self.ch:
            self.white()
            if self.ch == "{":
                o[idx] = self.object()
                idx += 1
                continue
            if self.ch == "}":
                self.depth -= 1
                self.next_chr()
                if k:
                    o[idx] = k
                if not [key for key in o if isinstance(key, str)]:
                    ar: list[LuaValue] = []
                    for key, val in o.items():
                        ar.insert(key, val)
                    return ar
                return o  # or here
            k = self.string() if self.ch == '"' else self.value()
            self.white()
            if self.ch == "=":
                self.next_chr()
                self.white()
                o[k] = self.value()
                idx += 1
                k = ""
            elif self.ch == ",":
                self.next_chr()
                self.white()
                o[idx] = k
                idx += 1
                k = ""
        log.error("Unexpected end of table while parsing Lua string.")  # Bad exit here
        return None

    def word(self) -> str | bool | None:
        """Parse a bare word: true, false, or an identifier."""
        s = ""
        if self.ch != "\n":
            s = self.ch
        while self.next_chr():
            if self.ch.isalnum():
                s += self.ch
            else:
                if re.match("^true$", s, re.IGNORECASE):
                    return True
                if re.match("^false$", s, re.IGNORECASE):
                    return False
                return str(s)
        return None

    def number(self) -> int | float | str:
        """Parse a number."""
        n = ""
        flt = False
        if self.ch == "-":
            n = "-"
            self.next_chr()
            if not self.ch or not self.ch.isdigit():
                log.error("Malformed number (no digits after initial minus)")
                return 0
        while self.ch and self.ch.isdigit():
            n += self.ch
            self.next_chr()
        if self.ch and self.ch == ".":
            n += self.ch
            flt = True
            self.next_chr()
            if not self.ch or not self.ch.isdigit():
                log.error("Malformed number (no digits after decimal point)")
                return n + "0"
            while self.ch and self.ch.isdigit():
                n += self.ch
                self.next_chr()
        if flt:
            return float(n)
        return int(n)
