from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class StrippedUpadeśa:
    raw_input: str
    clean_stem: str
    it_tags: set[str]
    elided_chars: list[str]


class AnubandhaEngine:
    """Formal Pāṇinian It-Saṃjñā stripping & Anubandha extraction processor.
    
    Implements sūtras 1.3.2 through 1.3.9.
    """

    @classmethod
    def strip_it_tags(cls, upadesa: str, is_pratyaya: bool = False) -> StrippedUpadeśa:
        """Executes classical tag elision pipeline."""
        tags: set[str] = set()
        elided: list[str] = []
        stem = upadesa

        if not stem:
            return StrippedUpadeśa(upadesa, "", tags, elided)

        # 1.3.3 Halantyam (Final consonant is It)
        # 1.3.4 Na vibhaktau tusmāḥ (Exception: dental, s, m in vibhaktis are not It)
        if stem[-1] in "kghṅcjñṭḍṇtdnpbmyrlvśṣsh":
            if is_pratyaya and stem[-1] in "tdnsm":
                pass # Exempt per 1.3.4
            else:
                elided.append(stem[-1])
                tags.add(f"final_{stem[-1]}")
                stem = stem[:-1]

        # 1.3.5 Ādir ñiṭuḍavaḥ (Initial ñi, ṭu, ḍu in dhātu)
        if not is_pratyaya:
            for pref in ("ñi", "ṭu", "ḍu"):
                if stem.startswith(pref):
                    elided.append(pref)
                    tags.add(f"init_{pref}")
                    stem = stem[len(pref):]
                    break

        # 1.3.6 Ṣaḥ pratyayasya (Initial ṣ in suffix)
        if is_pratyaya and stem.startswith("ṣ"):
            elided.append("ṣ")
            tags.add("ṣit")
            stem = stem[1:]

        # 1.3.7 Cuṭū (Initial palatal/retroflex in suffix)
        if is_pratyaya and stem and stem[0] in "cjñṭḍṇ":
            elided.append(stem[0])
            tags.add(f"{stem[0]}it")
            stem = stem[1:]

        # 1.3.8 Laśakavataddhite (Initial l, ś, ku in non-taddhita suffix)
        if is_pratyaya and stem and stem[0] in "lśkghṅ":
            elided.append(stem[0])
            tags.add(f"{stem[0]}it")
            stem = stem[1:]

        # Extract semantic tag meanings
        if any(t.endswith("p") for t in tags):
            tags.add("pit") # Udatta accent
        if any(t.endswith("ṅ") for t in tags):
            tags.add("ṅit") # Atmanepada

        return StrippedUpadeśa(upadesa, stem, tags, elided)
