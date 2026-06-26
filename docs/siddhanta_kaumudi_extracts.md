# Grammatical Extracts & Structural Analysis: Vaiyākaraṇa Siddhānta Kaumudī

Authored by **Bhaṭṭoji Dīkṣita** (c. 1600 CE), the *Vaiyākaraṇa Siddhānta Kaumudī* (*Siddhānta Kaumudī*) is the definitive encyclopedic re-organization of Pāṇini’s entire *Aṣṭādhyāyī*. While *Laghu* covers ~1,270 entry-level sūtras, *Siddhānta Kaumudī* encodes **all ~3,983 Pāṇinian sūtras** into a unified, formal *Prakriyā* architecture.

---

## 1. Encyclopedic Scope & Architecture

Bhaṭṭoji Dīkṣita established that computational completeness requires capturing every edge case, dialectal Vedic variant, secondary derivative (*Taddhita*), and tonal pitch rule without compromising the formal algebraic invariants of Pāṇini.

### Thematic Order of *Prakaraṇas* (Comprehensive Curriculum)
1. **Saṃjñā Prakaraṇam**: Meta-language definitions & axiom declarations.
2. **Paribhāṣā Prakaraṇam**: Conflict resolution meta-rules (*Vipratiṣedhe paraṃ kāryam*, *Asiddhavat atrābhāsāt*).
3. **Pañcasandhi Prakaraṇam**: Five-fold euphonic boundary matrix (*Ac*, *Prakṛtibhāva*, *Hal*, *Visarga*, *Svaādi*).
4. **Ṣaḍliṅga Prakaraṇam (Subanta)**: Six-fold nominal stem declensions across three genders and two endings (*Ajanta* vs. *Halanta*).
5. **Strīpratyaya Prakaraṇam**: Gender transformation morphology (*Ṭāp*, *Ṅīp*, *Ṅīṣ*, *Ṅīn*).
6. **Kāraka Prakaraṇam**: Deep semantic case relations (*Apādāna*, *Sampradāna*, *Karanā*, *Adhikaraṇa*, *Karma*, *Kartā*).
7. **Samāsa Prakaraṇam**: Recursive syntax tree compounding (*Avyayibhāva*, *Tatpuruṣa*, *Bahuvrīhi*, *Dvandva*).
8. **Taddhita Prakaraṇam**: Secondary nominal derivation (~1,100 sūtras governing patronymics, abstracts, adjectives).
9. **Daśagaṇa Tiṅanta Prakaraṇam**: Complete verbal morphology across 10 classes and 10 lakāras.
10. **Sannanta / Yaṅanta / Nāmadhātu**: Derivative verbal stems (Desideratives, Intensives, Denominatives).
11. **Kṛdanta / Uṇādi Prakaraṇam**: Primary verbal derivatives & irregular archaic nouns.
12. **Vaidikī & Svara Prakaraṇam**: Vedic liturgical syntax and pitch accent computation (*Udātta*, *Anudātta*, *Svarita*).

---

## 2. Core Architectural Principles for Engine Scaling

### A. Strict Separation of *Sapāda* and *Tripādī*
Bhaṭṭoji Dīkṣita rigorously enforces Pāṇini 8.2.1 (*Pūrvatrāsiddham*). The engine must split execution into two distinct mathematical rings:
- **Ring 1: Sapāda Saptādhyāyī (Sūtras 1.1.1 to 8.1.74)**:
  Operates as a **Recursive Graph Rewrite Engine**. Rules can feed back into each other until a stable fixed point is reached.
- **Ring 2: Tripādī (Sūtras 8.2.1 to 8.4.68)**:
  Operates as a **Strictly Sequential Pipeline**. Later rules cannot be seen by earlier rules, and output cannot re-trigger earlier *Sapāda* rules.

### B. The 4-Tier Conflict Resolution Matrix (*Paribhāṣā Hierarchy*)
When multiple sūtras match simultaneously, *Siddhānta Kaumudī* establishes deterministic arbitration:
$$\text{Apavāda (Specific Exception)} \succ \text{Nitya (Indestructible)} \succ \text{Antaraṅga (Internal Scope)} \succ \text{Para/Pūrva (Numeration Priority)}$$
