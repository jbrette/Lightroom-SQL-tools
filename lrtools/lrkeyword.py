"""LRKeywords class for Lightroom keywords manipulation."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .lrcat import LRCatDB

# A keyword's parent: the id of the parent keyword, "" for the root keyword's children.
type KeywordParent = int | str | None


class LRKeywords:
    """Keywords manipulation."""

    def __init__(self, lrdb: LRCatDB) -> None:
        """Init from lrdb, a LRCatDB instance."""
        self.lrdb = lrdb
        self.tree: dict[KeywordParent, list[int]] = {}
        self.rootid: int | None = None
        self.id2keyname: dict[int, str] = {}
        self.hierachical_keywords: dict[int, str] = {}
        self.hkeyname2id: dict[str, int] = {}

    def _init_hierarchical_keywords(self) -> None:
        """Initialize and build hierarchical keywords."""
        self.lrdb.cursor.execute("SELECT id_local, name, parent FROM AgLibraryKeyword")
        self.tree = {}
        self.id2keyname = {}
        for pid, name, db_parent in self.lrdb.cursor.fetchall():
            self.id2keyname[pid] = name or ""
            parent = db_parent
            if not parent:
                self.rootid = pid
                parent = ""
            if parent not in self.tree:
                self.tree[parent] = []
            self.tree[parent].append(pid)

        # dict keyword_id -> hierarchical name
        self.hierachical_keywords = self._build_hierachical_keywords()
        # dict hierarchical name -> keyword_id
        self.hkeyname2id = {v: k for k, v in self.hierachical_keywords.items()}

    def _showtree(self, pid: int | None, level: int) -> None:
        """Display keywords in hierachical format."""
        if not self.tree:
            self._init_hierarchical_keywords()
        if not pid:
            pid = self.rootid
        for k in self.tree[pid]:
            print(level * " ", self.id2keyname[k])  # noqa: T201 - the method's purpose is to print
            if k in self.tree:
                self._showtree(k, level + 2)

    def show_hierarchical_indented(self) -> None:
        """Display keywords in hierachical indented format."""
        self._showtree(self.rootid, 0)

    def _build_hierachical_keywords(self) -> dict[int, str]:
        """Build list of keywords in hierachical form."""

        def _build(pid: KeywordParent, hname: str, hkeys: dict[int, str]) -> None:
            hname_next = hname
            if hname:
                hname_next += "|"
            for k in self.tree[pid]:
                if k in self.tree:
                    _build(k, f"{hname_next}{self.id2keyname[k]}", hkeys)
                hkeys[k] = f"{hname_next}{self.id2keyname[k]}"

        if not self.tree:
            self._init_hierarchical_keywords()
        hkeywords: dict[int, str] = {}
        _build(self.rootid, "", hkeywords)
        return hkeywords

    def get_hierarchical_list(self) -> list[str]:
        """Return hierarchical list sorted by keywords."""
        if not self.hierachical_keywords:
            self._init_hierarchical_keywords()
        return sorted(self.hierachical_keywords.values())

    def get_hierarchical_name(self, idkey: int) -> str:
        """Return hierarchical name of key index."""
        if not self.hierachical_keywords:
            self._init_hierarchical_keywords()
        return self.hierachical_keywords[idkey]

    def get_name(self, idkey: int) -> str:
        """Return name of key index."""
        if not self.hierachical_keywords:
            self._init_hierarchical_keywords()
        return self.hierachical_keywords[idkey].split("|")[-1]

    def get_id(self, hkname: str) -> int:
        """Return key id from hiecharchical key name."""
        if not self.hkeyname2id:
            self._init_hierarchical_keywords()
        return self.hkeyname2id[hkname]

    def all_persons(self) -> list[Any]:
        """Select all persons keywords."""
        self.lrdb.cursor.execute(
            'SELECT name FROM AgLibraryKeyword WHERE keywordType="person" ORDER BY name'
        )
        return self.lrdb.cursor.fetchall()

    def photo_keys(
        self, idphoto: int, *, include_persons: bool = True
    ) -> tuple[list[str], list[str]]:
        """Get photo keywords.

        Parameters:
            idphoto : (int) local_id from table Adobe_Image
            include_persons : (bool) include keywordType="person" if True
        Return :
            list_hierarchical_keywords , list_keywords
        """
        keynames = []
        hkeynames = []
        if include_persons:
            self.lrdb.cursor.execute(f"SELECT tag FROM AgLibraryKeywordImage WHERE image={idphoto}")
            for (idkey,) in self.lrdb.cursor.fetchall():
                hkeynames.append(self.get_hierarchical_name(idkey))
                keynames.append(self.get_name(idkey))
        else:
            self.lrdb.cursor.execute(
                f"SELECT tag, name, keywordType FROM AgLibraryKeywordImage ki JOIN AgLibraryKeyword k ON ki.tag = k.id_local WHERE image={idphoto}"
            )
            for idkey, name, ktype in self.lrdb.cursor.fetchall():
                if ktype == "person":
                    continue
                hkeynames.append(self.get_hierarchical_name(idkey))
                keynames.append(name)
        return hkeynames, keynames

    def hierachical_indexes(self, key_part: str, operation: str) -> list[int]:
        """Find keywords containing key_part, and all keyword indexes hierachically under them.

        - key_part : (str) keyword or part of keyword without joker '%'
        - operation : operation of smart function. Can be: all, any, noneOf, words, beginsWith, endsWith
            * words : find complete word in keywords (ex: key_part="sport", returns "sport", "professional sport" , but not "sporting", "transport")
            * beginsWith : complete word in each keyword begins with key_part
            * endsWith : complete word in each keyword ends with key_part
            * all, any, noneOf : find all occurences of key_part in keywords
        """
        key_part = key_part.lower()
        key = f'"%{key_part}%"'

        def find_sub_indexes(index: int, indexes: list[int]) -> None:
            self.lrdb.cursor.execute(
                f"SELECT id_local FROM AgLibraryKeyword WHERE parent = {index}"
            )
            sub_indexes = self.lrdb.cursor.fetchall()
            for (sub_index,) in sub_indexes:
                indexes.append(int(sub_index))
                find_sub_indexes(int(sub_index), indexes)

        rows: list[tuple[int]]
        if operation == "words":
            self.lrdb.cursor.execute(
                f"SELECT id_local, lc_name FROM AgLibraryKeyword WHERE lc_name LIKE {key}"
            )
            # check if complete word in keyword
            rows = [
                (row[0],)
                for row in self.lrdb.cursor.fetchall()
                if key_part.lower() in row[1].split()
            ]
        elif operation == "endsWith":
            self.lrdb.cursor.execute(
                f"SELECT id_local, lc_name FROM AgLibraryKeyword WHERE lc_name LIKE {key}"
            )
            rows = [
                (row[0],)
                for row in self.lrdb.cursor.fetchall()
                for word in row[1].split()
                if word.endswith(key_part)
            ]
        elif operation == "beginsWith":
            self.lrdb.cursor.execute(
                f"SELECT id_local, lc_name FROM AgLibraryKeyword WHERE lc_name LIKE {key}"
            )
            rows = [
                (row[0],)
                for row in self.lrdb.cursor.fetchall()
                for word in row[1].split()
                if word.startswith(key_part)
            ]
        else:
            rows = self.lrdb.cursor.execute(
                f"SELECT id_local FROM AgLibraryKeyword WHERE lc_name LIKE {key}"
            ).fetchall()
        if not rows:
            return []
        indexes: list[int] = []
        for (index,) in rows:
            indexes += [index]
            find_sub_indexes(index, indexes)
        return indexes
