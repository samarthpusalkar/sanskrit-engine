import os
import json
import time
from typing import Dict, Any
from .rule_database import RuleDatabase

class MockLLMClient:
    """
    Stub for the LLM API (e.g. Gemini 1.5 Pro).
    In production, this translates unstructured Sanskrit/Hindi into our strict JSON Schema.
    """
    def generate_json_rule(self, sutra_text: str, meaning_text: str) -> Dict[str, Any]:
        # Simulating LLM parsing the sutra "akaḥ savarṇe dīrghaḥ"
        if "सवर्णे दीर्घः" in sutra_text or "dirgha" in meaning_text.lower():
            return {
                "rule_id": "6.1.101",
                "name": "akaha savarne dirghah",
                "category": "vidhi",
                "priority": 100,
                "domain": ["verb", "noun"],
                "conditions": {
                    "target": {"ends_with_vowel": ["a", "i", "u", "ṛ", "ḷ"]},
                    "right_context": {"starts_with_savarna": True}
                },
                "operation": {
                    "type": "lambda",
                    # Python lambda to merge final and initial vowels into a long vowel (dīrgha)
                    "executable": "lambda t, env: (t[0][:-1] + 'ā' if t[0][-1] == 'a' else t[0], t[1][1:])"
                }
            }
        
        # Fallback dummy rule
        return {
            "rule_id": "0.0.0",
            "name": "Dummy Rule",
            "operation": {
                "type": "lambda",
                "executable": "lambda t, env: t"
            }
        }

class AshtadhyayiCompiler:
    """
    Agentic compiler that reads ashtadhyayi-data, prompts the LLM, validates, and commits.
    """
    def __init__(self, db_path: str):
        self.db = RuleDatabase(db_path)
        self.llm = MockLLMClient()

    def test_compiled_rule(self, rule_data: Dict[str, Any]) -> bool:
        """
        Agentic feedback loop: Test the LLM-generated lambda to ensure it compiles
        and doesn't throw syntax errors.
        """
        try:
            # We mock a PaniniRule to check if compilation fails
            from .rule_database import PaniniRule
            temp_rule = PaniniRule(rule_data)
            
            # Simple smoke test on the lambda
            if temp_rule.operation_data.get("type") == "lambda":
                mock_token = ("rāma", "avatāra")
                temp_rule.operation_func(mock_token, {})
            return True
        except Exception as e:
            print(f"Validation failed for {rule_data.get('rule_id')}: {e}")
            return False

    def compile_sutras(self, sutras: list[dict]):
        print(f"Starting compilation of {len(sutras)} sutras...")
        for sutra in sutras:
            print(f"Compiling Sutra: {sutra['text']}")
            
            # 1. Ask LLM to generate the JSON rule
            rule_data = self.llm.generate_json_rule(sutra["text"], sutra["meaning"])
            
            # 2. Agentic Validation Loop
            success = self.test_compiled_rule(rule_data)
            if not success:
                print("-> LLM output failed unit tests. In production, feedback stack trace to LLM...")
                # self.llm.fix_json_rule(rule_data, error_trace)
                continue
                
            # 3. Commit to Database
            self.db.insert_rule(rule_data)
            print(f"-> Successfully committed Rule {rule_data['rule_id']} to Database.\n")

if __name__ == "__main__":
    print("--- Paninian Database Automation Pipeline ---")
    
    # Mock data fetched from https://github.com/samarthpusalkar/ashtadhyayi-data
    mock_sutras = [
        {"text": "अकः सवर्णे दीर्घः ॥ ६।१।१०१ ॥", "meaning": "When ak (a, i, u, r, l) is followed by a savarna (similar vowel), dirgha (long vowel) is the single substitute for both."},
        {"text": "इको यणचि ॥ ६।१।७७ ॥", "meaning": "yan (y, v, r, l) is substituted for ik (i, u, r, l) when ach (vowels) follows."}
    ]
    
    db_file = "data/ashtadhyayi_db.json"
    os.makedirs("data", exist_ok=True)
    
    compiler = AshtadhyayiCompiler(db_file)
    compiler.compile_sutras(mock_sutras)
    
    print("Database built successfully!")
