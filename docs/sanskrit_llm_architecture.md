# Sanskrit LLM Architecture Concepts

This document outlines proposed architectural design choices for a Large Language Model (LLM) tailored specifically for the Sanskrit language. It focuses on taking advantage of Sanskrit's rigorous morphological structure and decoupling knowledge from linguistic capabilities.

## 1. Vector-based Root Tokenization

Standard LLMs tokenize text into arbitrary subword chunks using algorithms like BPE (Byte Pair Encoding) or SentencePiece, mapping each chunk to a scalar integer ID. For a morphologically rich and structurally perfectly-defined language like Sanskrit (governed by Paninian grammar), this approach discards critical grammatical derivation rules. 

A proposed architecture uses **Vector-based Root Tokenization**, where each input is encoded into a multi-dimensional vector representing the semantic root and its exact morphological transformations.

### Token Representation

Instead of a single scalar ID $T_i$, an input word is parsed and represented as a multi-dimensional tuple or tensor:
`Token_Vector = [root_id, verb_mod_id, noun_mod_id, tense_mod_id, meta_id]`

*   **`root_id`**: The core semantic root (dhātu or prātipadika), e.g., *gam* (to go), *kṛ* (to do).
*   **`verb_mod_id`**: Action transformations (e.g., causative, desiderative, prefixes/upasargas).
*   **`noun_mod_id`**: Declension properties (vibhakti - case, vacana - number, liṅga - gender).
*   **`tense_mod_id`**: Tense and mood markers (lakāras).
*   **`meta_id`**: Additional syntactic markers.

### Advantages and Mechanics

Because all combinations of roots and transformations in Sanskrit are structurally coherent and deterministic (subject to known exceptions), this tokenization operates akin to tensor math. 

When passed to the embedding layer, this becomes a highly complex but **semantically rich input**. The model no longer has to guess that *gacchati* and *agacchat* are related; the shared `root_id` explicitly tells the model they share core semantics, while the different `tense_mod_id` explicitly defines the temporal shift. 

## 2. Hardcoded vs. Learned Grammatical Attention Filters

Sanskrit features strict meta-rules for syntax, such as subject-verb agreement (e.g., an active verb must match the number and person of the agent). The architecture must incorporate these state-machine-like rules.

### Approach A: Hardcoded Attention Masks (Rule-Based Filter)

We can inject grammatical rules directly into the transformer architecture as an attention filter. 
*   **Implementation**: Create an adjacency matrix or mask based on Paninian parsing algorithms. If word $A$ (subject, dual) and word $B$ (verb, singular) violate agreement rules, a large negative penalty is applied in the attention mechanism.
*   **Pros**: Guarantees grammatical correctness based on known state machine rules.
*   **Cons**: Rigid; may struggle with poetry, ellipses, or informal texts where rules are implicitly understood or bent.

### Approach B: Learned Mapping via Q-K Matrices (Data-Driven)

As hypothesized, it is often better if the model learns this mapping filter itself. 
*   **Implementation**: By supplying the richly structured vector tokens, the standard attention mechanism's Query ($Q$) and Key ($K$) weight matrices naturally learn to discover grammatical dependencies. The linear projections $W_Q, W_K$ will learn to attend to specific sub-dimensions of the token vector. For example, the matrix learns to yield high attention scores only when the "number" dimension of a noun token aligns with the "number" dimension of a verb token.
*   **Conclusion**: Providing the vector tokenization is usually sufficient for standard transformer attention blocks to implicitly learn these state-machine rules and exceptions gracefully without hardcoding masks.

## 3. Decoupling Fact Learning from Semantic/Grammar Processing

A significant challenge in current LLMs is the entanglement of language understanding (grammar, syntax, reasoning) and world knowledge (facts). To build a system where memory and facts are swappable without affecting language capabilities, deliberate architectural decoupling is required.

### Goal
Separate the "Semantic Processor" (how to speak, parse, and reason in Sanskrit) from the "Knowledge Base" (factual assertions).

### Architectural Solutions for Decoupling

#### 1. Retrieval-Augmented Generation (RAG) as Core Architecture
The most reliable way to separate facts is to completely remove them from the model's parameters.
*   The core LLM is trained *exclusively* on language structure, grammar rules, reasoning, and translation capabilities.
*   Factual knowledge is stored in an external Vector Database or Knowledge Graph.
*   **Swapping Memory**: To change what the model knows, you simply swap the external database. The model's ability to formulate grammatically perfect Sanskrit remains intact.

#### 2. Parameter-Efficient Fine-Tuning (Adapters / LoRA)
Train the base model thoroughly on Sanskrit language capabilities and freeze those weights.
*   Train separate Low-Rank Adapters (LoRAs) strictly on different domains of factual knowledge (e.g., one adapter for Ayurveda texts, another for historical chronicles).
*   **Swapping Memory**: Load and unload these adapters dynamically at inference time to change the model's factual context while maintaining the frozen base grammatical parameters.

#### 3. Continuous Distillation from System Prompts
The architecture can extend decoupling to how facts are injected via System Prompts vs. Memory.
*   **Working Memory (System Prompt)**: Used for highly specific, ephemeral facts injected at runtime.
*   **Long-Term Memory (Adapters/RAG)**: Used for permanent factual knowledge.
*   **Deliberate Shift**: A background process can be designed to monitor frequently injected facts in system prompts. Once a fact reaches a threshold of usage, the system triggers a job to "bake" this fact into the Long-Term Memory (e.g., updating the RAG database or fine-tuning a background LoRA). This allows the system to seamlessly transition a fact from prompt-engineering to permanent memory, freeing up the prompt context window.
