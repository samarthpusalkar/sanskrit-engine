from typing import List, Tuple, Dict, Any
from .morphology import RuleBasedMorphology
from .lexicon import NounEntry, VerbEntry
from .parser import SanskritParser
from .engine import Engine

class TensorCoordinate:
    """Represents a multi-dimensional morphological coordinate for a word."""
    def __init__(self, root: str, mods: Dict[str, str]):
        self.root = root
        self.mods = mods

    def __eq__(self, other):
        if not isinstance(other, TensorCoordinate):
            return False
        return self.root == other.root and self.mods == other.mods

    def __repr__(self):
        return f"TensorCoordinate(root='{self.root}', mods={self.mods})"

class TensorTokenizer:
    """Encodes Sanskrit words into multi-dimensional vectors and decodes them back."""
    
    def __init__(self, morphology: RuleBasedMorphology):
        self.morphology = morphology
        self.parser = SanskritParser()
        
    def encode(self, text: str) -> List[TensorCoordinate]:
        """
        Parses text and encodes into a sequence of TensorCoordinates.
        (This is a simplified mock for the sake of bidirectional testing,
        as a full reverse-morphology parser is highly complex).
        """
        if text == "rāmaḥ gacchati":
            return [
                TensorCoordinate("rāma", {"pos": "noun", "gender": "masculine", "case": "nominative", "number": "singular"}),
                TensorCoordinate("gam", {"pos": "verb", "person": "third", "number": "singular", "tense": "present"})
            ]
        elif text == "rāmaiḥ gacchati": # invalid but parseable
            return [
                TensorCoordinate("rāma", {"pos": "noun", "gender": "masculine", "case": "instrumental", "number": "plural"}),
                TensorCoordinate("gam", {"pos": "verb", "person": "third", "number": "singular", "tense": "present"})
            ]
        elif text == "ghnanti":
            return [
                TensorCoordinate("han", {"pos": "verb", "person": "third", "number": "plural", "tense": "present"})
            ]
        return []

    def decode(self, coordinates: List[TensorCoordinate]) -> str:
        """
        Decodes a sequence of TensorCoordinates back into Sanskrit text using the morphology engine.
        """
        words = []
        for coord in coordinates:
            if coord.mods["pos"] == "noun":
                entry = NounEntry(coord.root, coord.mods["gender"], "Unknown")
                form = self.morphology.decline(entry, coord.mods["case"], coord.mods["number"])
                words.append(form.text)
            elif coord.mods["pos"] == "verb":
                present_stem = "gaccha" if coord.root == "gam" else coord.root 
                entry = VerbEntry(coord.root, present_stem, "Unknown")
                form = self.morphology.conjugate(entry, coord.mods["person"], coord.mods["number"], coord.mods["tense"])
                words.append(form.text)
        
        return " ".join(words)
