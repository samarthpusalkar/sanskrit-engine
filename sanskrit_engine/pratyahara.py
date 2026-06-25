from __future__ import annotations

import json
from pathlib import Path


class PratyaharaResolver:
    """Fast resolver for Shiva Sutra pratyaharas.

    This is enough for engine mechanics. Extend/verify set inventory against
    primary source data before serious linguistic use.
    """

    _SHIVA_SUTRAS: tuple[tuple[str, ...], ...] = (
        ("a", "i", "u", "ṇ"),
        ("ṛ", "ḷ", "k"),
        ("e", "o", "ṅ"),
        ("ai", "au", "c"),
        ("ha", "ya", "va", "ra", "ṭ"),
        ("la", "ṇ"),
        ("ña", "ma", "ṅa", "ṇa", "na", "m"),
        ("jha", "bha", "ñ"),
        ("gha", "ḍha", "dha", "ṣ"),
        ("ja", "ba", "ga", "ḍa", "da", "ś"),
        ("kha", "pha", "cha", "ṭha", "tha", "ca", "ṭa", "ta", "v"),
        ("ka", "pa", "y"),
        ("śa", "ṣa", "sa", "r"),
        ("ha", "l"),
    )

    def __init__(self) -> None:
        self.shiva_sutras = [
            "a i u Ṇ", "ṛ ḷ K", "e o Ṅ", "ai au C",
            "ha ya va ra Ṭ", "la Ṇ", "ña ma ṅa ṇa na M",
            "jha bha Ñ", "gha ḍha dha Ṣ", "ja ba ga ḍa da Ś",
            "kha pha cha ṭha tha ca ṭa ta V", "ka pa Y",
            "śa ṣa sa R", "ha L"
        ]
        self.tokens = " ".join(self.shiva_sutras).split()
        self._phonemes: list[str] = []
        self._markers: dict[str, int] = {}
        for sutra in self._SHIVA_SUTRAS:
            for item in sutra:
                if self._is_marker(item):
                    self._markers[item] = len(self._phonemes)
                else:
                    self._phonemes.append(item)
        self._cache: dict[str, frozenset[str]] = {}

    @classmethod
    def from_mapping(cls, mapping: dict[str, list[str]]) -> "PratyaharaResolver":
        resolver = cls()
        resolver._cache = {
            name: frozenset(items)
            for name, items in mapping.items()
        }
        return resolver

    @classmethod
    def from_ashtadhyayi_data(cls, path: str | Path) -> "PratyaharaResolver":
        """Load `ashtadhyayi-data/pratyahara/data.txt` JSON."""

        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        records = raw["data"] if isinstance(raw, dict) and "data" in raw else raw
        mapping: dict[str, list[str]] = {}
        for record in records:
            name = record["name"].strip()
            items = [
                item.strip()
                for item in record["list"].split(",")
                if item.strip()
            ]
            # Same name can occur with different marker source. Keep first exact
            # source entry and expose later duplicates with sutra-number suffix.
            if name in mapping:
                suffix = record.get("sutranum", "").strip("[]")
                name = f"{name}@{suffix}" if suffix else name
            mapping[name] = items
        return cls.from_mapping(mapping)

    def resolve(self, name: str) -> frozenset[str]:
        if name in self._cache:
            return self._cache[name]
        if len(name) < 2:
            raise KeyError(f"Invalid pratyahara: {name}")

        start = name[:-1]
        marker = name[-1]
        if start not in self._phonemes or marker not in self._markers:
            raise KeyError(f"Unknown pratyahara: {name}")

        start_index = self._phonemes.index(start)
        end_index = self._markers[marker]
        if end_index <= start_index:
            raise KeyError(f"Invalid pratyahara span: {name}")

        value = frozenset(self._phonemes[start_index:end_index])
        self._cache[name] = value
        return value

    def contains(self, pratyahara: str, phoneme: str) -> bool:
        return phoneme in self.resolve(pratyahara)

    def decode(self, pratyahara: str) -> list[str]:
        if not pratyahara or len(pratyahara) < 2:
            return []
        start_letter = pratyahara[:-1]
        end_marker = pratyahara[-1].upper()

        if start_letter not in self.tokens and (start_letter + "a") in self.tokens:
            start_letter += "a"

        try:
            start_idx = self.tokens.index(start_letter)
            if pratyahara.lower() in {"iṇ", "aṇ@6", "aṇ2"}:
                first_n = self.tokens.index("Ṇ", start_idx)
                end_idx = self.tokens.index("Ṇ", first_n + 1)
            else:
                end_idx = self.tokens.index(end_marker, start_idx)
        except ValueError:
            return []

        raw_slice = self.tokens[start_idx:end_idx]
        result = []
        for char in raw_slice:
            if char.islower():
                if len(char) > 1 and char.endswith("a"):
                    result.append(char[:-1])
                else:
                    result.append(char)
        return result

    @staticmethod
    def _is_marker(value: str) -> bool:
        return value in {"ṇ", "k", "ṅ", "c", "ṭ", "m", "ñ", "ṣ", "ś", "v", "y", "r", "l"}
