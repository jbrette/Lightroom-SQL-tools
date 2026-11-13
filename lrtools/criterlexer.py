"""Lexical parser for criteria."""

import re
from typing import ClassVar

# a token: (kind, (key, value)) for KEYVAL, (kind, None) for operators and parentheses
type Token = tuple[str, tuple[str, str] | None]


class CriterLexer:
    """Lexical parser for criteria."""

    # List of tokens accepted after specific token
    RULES_FOLLOW: ClassVar[dict[str | None, list[str]]] = {
        None: ["LPAR", "KEYVAL"],
        "KEYVAL": ["OR", "AND", "RPAR"],
        "OR": ["KEYVAL", "LPAR"],
        "AND": ["KEYVAL", "LPAR"],
        "LPAR": ["KEYVAL", "LPAR"],
        "RPAR": ["OR", "AND", "RPAR"],
    }

    # operator token kinds and their regex, tried in this order
    OPERATORS: ClassVar[list[tuple[str, str]]] = [
        ("LPAR", r"(\() *"),
        ("RPAR", r"(\)) *"),
        ("AND", r", *"),
        ("OR", r"\| *"),
    ]

    def __init__(self, criters: str) -> None:
        """Prepare the parsing of the criteria string."""
        self.criters = criters
        self.tokens: list[Token] = []
        self.last_error = ""

    def _parse_keyval(self) -> bool:
        """Parse KEY [= VALUE]."""
        #
        # get criter
        #
        _m = re.match(r"(\w+) *", self.criters)
        if not _m:
            return False
        key = _m.group(1).lower()
        self.criters = self.criters[_m.end() :]

        #
        # get value
        #
        _m = re.match(r" *= *", self.criters)
        if _m:
            self.criters = self.criters[_m.end() :]
            # regex from https://www.metaltoad.com/blog/regex-quoted-string-escapable-quotes
            _m = re.match(r' *((?<![\\])[\'"])((?:.(?!(?<![\\])\1))*.?)\1', self.criters)
            if _m:
                # regex return quote type ("') and string
                value = _m.group(2)
            else:
                _m = re.match(r" *([^,\|\)\(]+)", self.criters)
                if _m:
                    # spaces before next operator are not part of value (use quotes to keep them)
                    value = _m.group(1).rstrip()
                else:
                    self.last_error = f'No value for criterion "{key}"'
                    return False
            self.criters = self.criters[_m.end() :]
            self.tokens.append(("KEYVAL", (key, value)))

        else:
            # no value for criter
            value = "True"
            self.tokens.append(("KEYVAL", (key, value)))
        return True

    def parse(self, criters: str | None = None) -> bool:
        """Parse criters string."""
        if criters:
            self.criters = criters
        if not self.criters:
            return False

        while len(self.criters) > 0:
            self.criters = self.criters.strip()
            if len(self.criters) == 0:
                break

            #
            # parse "key = value"
            #
            if self._parse_keyval():
                continue
            if self.last_error:
                return False

            #
            # operators : '(', ')', AND ',' and OR '|'
            #
            if self._parse_operator():
                continue

            #
            # Finally : token error
            #
            self.last_error = f"Invalid token \042{self.criters.split(' ')[0]}\042"

            return False

        return self.check_syntax()

    def _parse_operator(self) -> bool:
        """Parse a parenthesis or an AND/OR operator."""
        for kind, regex in self.OPERATORS:
            _m = re.match(regex, self.criters)
            if _m:
                self.tokens.append((kind, None))
                self.criters = self.criters[_m.end() :]
                return True
        return False

    def check_syntax(self) -> bool:
        """Check criters syntax (only following token)."""
        prev_kind: str | None = None
        par_level = 0
        for kind, _ in self.tokens:
            if kind not in self.RULES_FOLLOW[prev_kind]:
                self.last_error = f'"{kind}" not allowed after "{prev_kind}"'
                return False
            if kind == "LPAR":
                par_level += 1
            elif kind == "RPAR":
                par_level -= 1
            prev_kind = kind
        if par_level != 0:
            self.last_error = "unbalanced parenthesis"
            return False
        return True
