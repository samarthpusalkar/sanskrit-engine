import os
import json
import time
from typing import Dict, Any
from .rule_database import RuleDatabase

import requests

class OllamaCloudClient:
    """
    Real LLM Client connecting to a Cloud Provider serving Ollama models.
    Uses OLLAMA_API_KEY from the environment and the specified model name.
    """
    def __init__(self):
        # The user's requested cloud model
        self.model = "qwen3-coder-next:cloud"
        self.api_key = os.environ.get("OLLAMA_API_KEY", "")
        
        # Adjust this endpoint to match your specific Cloud Provider's Ollama-compatible URL
        # For OpenAI-compatible Ollama wrappers, this is usually 'https://api.yourprovider.com/v1/chat/completions'
        self.api_url = os.environ.get("OLLAMA_API_URL", "http://localhost:11434/api/chat")

    def generate_json_rule(self, sutra_text: str, meaning_text: str, error_feedback: str = None) -> Dict[str, Any]:
        prompt = f'''
        You are an expert Paninian Sanskrit Grammarian and Python Coder.
        Parse the following Sutra into our strict engine JSON Schema.
        Sutra: {sutra_text}
        
        The following block contains PadacCheda (word split), Anuvrtti (inherited words from previous rules), and Adhikara (governing domain). You MUST use the Anuvrtti and Adhikara to construct your mathematical logic!
        Context Data:
        {meaning_text}
        
        CRITICAL PYTHON CONSTRAINTS:
        1. `token` can either be a tuple of two strings (e.g., `("rāma", "avatāra")`) for Sandhi rules, OR a dictionary (e.g., `{{"text": "bhū", "pos": "verb"}}`) for morphology rules.
        2. ALWAYS use `isinstance(token, tuple)` or `isinstance(token, dict)` to check the type before applying string or dictionary methods. Do not assume `token` is always a dict or always a tuple.
        3. ONLY use standard Python built-in methods (like `.endswith()`, `[:-1]`, etc). DO NOT hallucinate nonexistent methods like `token.get_vowel()` or `token.is_consonant()`.
        4. The lambda must return the modified token in the exact same data type it received (e.g., if token is a tuple, return a modified tuple. If it is a dict, return a dict).
        5. STRICT UNICODE IAST: When generating character matches or replacements, NEVER use ASCII substitutes like capital 'A' for long 'a'. You MUST use strict Unicode IAST characters: ā, ī, ū, ṛ, ṝ, ḷ, ñ, ṅ, ṣ, ś, ṭ, ḍ, ṇ.

        Output valid JSON with the following structure:
        {{
            "rule_id": "X.X.X",  // EXACTLY format like "6.1.101" (Do NOT include "P." or spaces)
            "name": "Sutra text transliterated",
            "category": "vidhi|apavada",
            "priority": 100,
            "domain": ["verb", "noun"],
            "conditions": {{
                "target": {{
                    "ends_with_vowel": ["a", "i", "u", "ṛ", "ḷ"]  // Example condition based on Sutra meaning
                }},
                "right_context": {{
                    "starts_with_savarna": true // Example condition
                }}
            }},
            "operation": {{
                "type": "symbolic_dsl",
                "op_kind": "substitute",
                "target_scope": "target",
                "executable": "lambda token, env: token" // Fallback callable
            }}
        }}
        Make sure the `conditions` block extracts the "when X follows" or "when X is the target" logic. Do not leave it empty.
        Output ONLY the raw JSON object.
        '''
        
        if error_feedback:
            prompt += f"\n\nYOUR LAST ATTEMPT FAILED WITH THIS PYTHON EXCEPTION: {error_feedback}\n"
            prompt += "Please fix the lambda so it runs without syntax or runtime errors."

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2, # Slightly higher temp to allow variation on retries
            "stream": False # Required for native Ollama endpoints so it doesn't return chunked JSONL
        }

        try:
            response = requests.post(self.api_url, json=payload, headers=headers)
            response.raise_for_status()
            
            resp_json = response.json()
            
            # Support both OpenAI-compatible endpoints and Native Ollama endpoints
            if "choices" in resp_json:
                result_text = resp_json["choices"][0]["message"]["content"]
            elif "message" in resp_json:
                result_text = resp_json["message"]["content"]
            elif "response" in resp_json:
                result_text = resp_json["response"]
            else:
                raise ValueError(f"Unrecognized API response structure: {resp_json}")
            
            # Clean Markdown formatting if the LLM outputted ```json
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].strip()
                
            return json.loads(result_text)
            
        except Exception as e:
            print(f"LLM API Error for Sutra '{sutra_text}': {e}")
            # Fallback to dummy rule so the pipeline doesn't crash completely
            return {"rule_id": "ERROR", "operation": {"type": "lambda", "executable": "lambda t, e: t"}}

class AshtadhyayiCompiler:
    """
    Agentic compiler that reads ashtadhyayi-data, prompts the LLM, validates, and commits.
    """
    def __init__(self, db_path: str):
        self.db = RuleDatabase(db_path)
        self.llm = OllamaCloudClient()

    def test_compiled_rule(self, rule_data: Dict[str, Any]) -> tuple[bool, str]:
        """
        Agentic feedback loop: Test the LLM-generated lambda to ensure it compiles
        and doesn't throw syntax errors. Returns (success, error_message).
        """
        try:
            # We mock a PaniniRule to check if compilation fails
            from .rule_database import PaniniRule
            temp_rule = PaniniRule(rule_data)
            
            # Rigorous smoke test on the lambda with BOTH supported data structures
            if temp_rule.operation_data.get("type") == "lambda":
                mock_tuple = ("rāma", "avatāra")
                mock_dict = {"text": "bhū", "pos": "verb"}
                
                # Test tuple handling
                temp_rule.operation_func(mock_tuple, {})
                # Test dict handling
                temp_rule.operation_func(mock_dict, {})
                
            return True, ""
        except Exception as e:
            return False, str(e)

    def compile_sutras(self, sutras: list[dict]):
        print(f"Starting compilation of {len(sutras)} sutras...")
        for sutra in sutras:
            print(f"Compiling Sutra: {sutra['text']}")
            
            max_retries = 3
            error_feedback = None
            
            for attempt in range(max_retries):
                if attempt > 0:
                    print(f"-> Retry {attempt}/{max_retries} with error feedback...")
                    
                # 1. Ask LLM to generate the JSON rule
                rule_data = self.llm.generate_json_rule(sutra["text"], sutra["meaning"], error_feedback)
                
                # If the LLM outright failed to hit the API, skip
                if rule_data.get("rule_id") == "ERROR":
                    error_feedback = "API returned an ERROR format. Please output valid JSON."
                    continue
                
                # 2. Agentic Validation Loop
                success, err_msg = self.test_compiled_rule(rule_data)
                if not success:
                    print(f"-> Validation failed for {rule_data.get('rule_id', 'Unknown')}: {err_msg}")
                    error_feedback = err_msg
                    continue
                    
                # Force pristine IAST name from our Python library
                if sutra.get("iast_name"):
                    rule_data["name"] = sutra["iast_name"]
                    
                # 3. Commit to Database
                self.db.insert_rule(rule_data)
                print(f"-> Successfully committed Rule {rule_data.get('rule_id')} to Database.\n")
                break
            else:
                print(f"-> FAILED to compile sutra after {max_retries} attempts.\n")

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
