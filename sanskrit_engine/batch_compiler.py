import os
import json
import time
from typing import Dict, Any
from .rule_database import RuleDatabase
from .llm_compiler import OllamaCloudClient, AshtadhyayiCompiler

class BatchCompiler:
    def __init__(self, raw_json_path: str, db_path: str):
        self.raw_json_path = raw_json_path
        self.db_path = db_path
        self.compiler = AshtadhyayiCompiler(self.db_path)
        
    def run_slice(self, limit: int = None):
        """Runs the compiler on a slice of rules for testing."""
        if not os.path.exists(self.raw_json_path):
            print(f"Error: {self.raw_json_path} not found.")
            return
            
        with open(self.raw_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        sutras_dict = data.get("sutras", {})
        
        # Extract existing compiled rule IDs to support resumable behavior
        if not os.path.exists(self.db_path):
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump({"rules": []}, f)
                
        with open(self.db_path, 'r', encoding='utf-8') as f:
            existing_db = json.load(f)
            existing_ids = {rule.get("rule_id") for rule in existing_db.get("rules", [])}
        
        print(f"Database currently holds {len(existing_ids)} compiled rules.")
        
        from indic_transliteration import sanscript
        from indic_transliteration.sanscript import transliterate
        
        sutras_to_process = []
        for key, s_obj in sutras_dict.items():
            rule_id = s_obj.get("Sutra_id", "").strip()
            
            # Skip if already compiled
            if rule_id in existing_ids:
                continue
                
            sutra_text = s_obj.get("Sutra_text", "")
            
            # Context Extraction
            padac_cheda = s_obj.get("PadacCheda", [])
            padas = [p.get("pada", "") for p in padac_cheda]
            
            anuvrtti_data = s_obj.get("Anuvrtti", [])
            anuvrtti_padas = []
            if isinstance(anuvrtti_data, list):
                for a in anuvrtti_data:
                    for p in a.get("padas", []):
                        if isinstance(p, dict):
                            anuvrtti_padas.append(p.get("pada", ""))
                        elif isinstance(p, str):
                            anuvrtti_padas.append(p)
                    
            influence = s_obj.get("Influence", "")
            
            context_meaning = f"PadacCheda (Words): {' '.join(padas)}\n"
            if anuvrtti_padas:
                context_meaning += f"Anuvrtti (Inherited Context from previous rules): {' '.join(anuvrtti_padas)}\n"
            if influence:
                context_meaning += f"Adhikara (Governing Domain): {influence}\n"
                
            perfect_iast = transliterate(sutra_text, sanscript.DEVANAGARI, sanscript.IAST)
            
            sutras_to_process.append({
                "id": rule_id,
                "text": f"{sutra_text} || {rule_id} ||",
                "meaning": context_meaning,
                "iast_name": perfect_iast
            })
            
            if limit and len(sutras_to_process) >= limit:
                break
                
        print(f"Starting batch job for {len(sutras_to_process)} sutras...\n")
        self.compiler.compile_sutras(sutras_to_process)

if __name__ == "__main__":
    batch = BatchCompiler("data/ashtadhyayi_raw.json", "data/ashtadhyayi_db.json")
    print("Testing batch processor on uncompiled rules...")
    batch.run_slice(limit=None) # No limit, process all remaining rules
