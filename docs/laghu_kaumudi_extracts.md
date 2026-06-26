# Grammatical Extracts & Structural Analysis: Laghusiddhānta Kaumudī

Authored by the 17th-century scholar **Varadarājācārya** (pupil of Bhaṭṭoji Dīkṣita), the *Laghusiddhānta Kaumudī* (*Laghu*) revolutionized pedagogical Sanskrit grammar. It re-architected Pāṇini's serial mathematical sūtras into a process-driven word derivation curriculum (*Prakriyā*).

---

## 1. Structural Paradigm: *Prakriyā* vs. *Adhyāya*

In Pāṇini’s *Aṣṭādhyāyī*, sūtras are arranged by formal computational dependencies (e.g., *Adhikāra* governing domains, *Asiddha* execution tiers). To form a single word e.g. `bhavati`, a computer or student must jump across Book 1, Book 3, Book 6, Book 7, and Book 8.

Varadarāja solved this by pioneering thematic process grouping:
- **Total Sūtra Count**: ~1,270 sūtras (approx. 30% of the *Aṣṭādhyāyī*).
- **Core Methodology**: Grouping all definitions, operational transforms, and exception overrides needed to synthesize a specific grammatical category into a single contiguous chapter (*Prakaraṇa*).

---

## 2. Exhaustive Chapter Progression (*Prakaraṇa Kramu*)

### Part I: Foundations & Combination
1. **Saṃjñā Prakaraṇam**: Technical definitions (*It*, *Lopa*, *Savarna*, *Saṃhitā*, *Pratyāhāra*).
2. **Sandhi Prakaraṇam**: Euphonic combinations across word and morpheme boundaries:
   - *Ac Sandhi* (Vowel combinations e.g. *Yan*, *Guna*, *Vrddhi*, *Dirgha*, *Ayavādi*).
   - *Hal Sandhi* (Consonant combinations e.g. *Scutva*, *Sṭutva*, *Jastva*, *Anunāsika*).
   - *Visarga Sandhi* (*Utva*, *Rutva*, *Lopa*).

### Part II: Nominal Morphology (*Subanta*)
3. **Ajanta Puṃliṅga / Strīliṅga / Napuṃsakaliṅga**: Vowel-ending noun declensions across 8 grammatical cases (*Vibhakti*) and 3 numbers (*Vacana*).
4. **Halanta Puṃliṅga / Strīliṅga / Napuṃsakaliṅga**: Consonant-ending noun declensions.
5. **Avyaya Prakaraṇam**: Indeclinable particles (*Svarādi*, *Cādi*, *Prefixes*).

### Part III: Verbal Morphology (*Tiṅanta*)
6. **Bhvādi Daśagaṇa Prakaraṇam**: Verbal root conjugations across the 10 Pāṇinian root classes (*Gaṇas*) and 10 Tense/Mood systems (*Lakāras*).

---

## 3. Key Algorithmic Extracts for Engine Architecture

### A. The *It-Saṃjñā* Stripping Pipeline
Before any morpheme enters derivation, Varadarāja establishes the mandatory 6-step metadata stripping sequence:
1. `1.3.2 Upadeśe'janunāsika it`: Nasalized vowels in foundational instruction are tags.
2. `1.3.3 Halantyam`: Final consonants in pratyayas/sūtras are tags.
3. `1.3.4 Na vibhaktau tusmāḥ`: Dental consonants, `s`, and `m` in nominal/verbal endings are *exempt* from deletion.
4. `1.3.5 Ādir ñiṭuḍavaḥ`: Initial `ñi`, `ṭu`, `ḍu` in dhātus are tags.
5. `1.3.6 Ṣaḥ pratyayasya`: Initial `ṣ` in suffixes is a tag.
6. `1.3.7 Cuṭū` & `1.3.8 Laśakavataddhite`: Suffix initial palatals/retroflexes and `l`, `ś`, `ku` are tags.
7. `1.3.9 Tasya lopaḥ`: Absolute elision of all tagged characters (*It*).

### B. The *Prakriyā Derivation Loop*
To model *Laghu* computationally, an engine cannot use static dictionaries. It must execute:
$$\text{Dhātu/Prātipadika} \longrightarrow \text{Tag Stripping} \longrightarrow \text{Pratyaya Introduction} \longrightarrow \text{Aṅga Operations (Guṇa/Vṛddhi)} \longrightarrow \text{Sandhi Integration} \longrightarrow \text{Pada Output}$$
