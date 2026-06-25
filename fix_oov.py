import re

file_path = "sanskrit_engine/tensor_tokenizer.py"
with open(file_path, "r") as f:
    content = f.read()

# Remove the dynamic OOV injection
bad_block = """            if tensor is None:
                # OOV Fallback: Dynamically inject into ROOT_VOCAB for 100% token fidelity
                from sanskrit_engine.config_index import ROOT_VOCAB, REV_ROOT
                if word not in ROOT_VOCAB:
                    new_id = max(ROOT_VOCAB.values()) + 1 if ROOT_VOCAB else 1
                    ROOT_VOCAB[word] = new_id
                    REV_ROOT[new_id] = word
                root_id = ROOT_VOCAB[word]
                tensor = [0, root_id, 0, POS_VOCAB["unknown_string"], 0, 0, 0]
                
            tensors.append(TensorCoordinate(tensor))"""

good_block = """            if tensor is None:
                # OOV Fallback: Subword / Character level encoding
                # Ensures serialization works across machines without mutating global memory
                for i, char in enumerate(word):
                    char_id = ord(char) # Using Unicode codepoint for simplicity
                    is_subword = 1 if i > 0 else 0 # 0=starts word, 1=continuation
                    tensors.append(TensorCoordinate([0, 0, 0, POS_VOCAB["unknown_string"], char_id, is_subword, 0]))
            else:
                tensors.append(TensorCoordinate(tensor))"""

content = content.replace(bad_block, good_block)

bad_decode = """            elif pos_str == "unknown_string":
                # For words that bypassed Paninian rules (OOV token fallback)
                from sanskrit_engine.config_index import REV_ROOT
                base_string = REV_ROOT.get(root_id, "[UNK]")"""

good_decode = """            elif pos_str == "unknown_string":
                # OOV Fallback: Reconstruct from Character Unicode
                base_string = chr(feat1)"""

content = content.replace(bad_decode, good_decode)

# Fix the join logic in decode
bad_join = """        # Reconstruct sentence
        # Applying external sandhi across boundaries could go here
        return " ".join(surface_forms)"""

good_join = """        # Reconstruct sentence
        result = ""
        for i, token in enumerate(coordinates):
            if i > 0:
                # Check subword continuation flag for OOV characters
                if token.vector[3] == POS_VOCAB["unknown_string"] and token.vector[5] == 1:
                    result += surface_forms[i]
                else:
                    result += " " + surface_forms[i]
            else:
                result += surface_forms[i]
        return result"""

content = content.replace(bad_join, good_join)

with open(file_path, "w") as f:
    f.write(content)

