# backend/app/services/faq_fastpath.py
# ─────────────────────────────────────────────────────────────────────────────
# Precomputed answers for frequently asked technical questions.
# Matches via keyword overlap + regex — returns in <10ms, no LLM call.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import re
from typing import Optional, Tuple, List
from app.services.translations_data import FAQ_TRANSLATIONS


# ── Pattern matchers ────────────────────────────────────────────────────────

def _tokens(text: str) -> set:
    return set(re.findall(r"\w+", text.lower()))


def _matches(text: str, required: set, optional: set = frozenset(), min_optional: int = 0) -> bool:
    tokens = _tokens(text)
    if not required.issubset(tokens):
        return False
    if optional and sum(1 for o in optional if o in tokens) < min_optional:
        return False
    return True


# ── FAQ entries ─────────────────────────────────────────────────────────────

_FAQ_ENTRIES: list[dict] = [
    {
        "id": "what_is_jitter",
        "match": lambda t: _matches(t, {"what", "jitter"}, {"is", "define", "definition", "meaning"}, 0) or "jitter" in t.lower() or "지터" in t or "抖动" in t or "ジッタ" in t,
        "reply": """## What Is Jitter?

**Jitter** is the deviation of a signal's timing from its ideal position. In digital communications and electronics, it refers to the short-term, non-cumulative variations of a digital signal's significant instants (e.g., rising or falling edges) from their ideal positions in time.

---

### Types of Jitter

| Type | Description |
|------|-------------|
| **Random Jitter (RJ)** | Unbounded, Gaussian-distributed; caused by thermal noise, shot noise |
| **Deterministic Jitter (DJ)** | Bounded, repeatable; caused by crosstalk, EMI, ISI |
| **Periodic Jitter (PJ)** | Subset of DJ; repeats at a known frequency |
| **Data-Dependent Jitter (DDJ)** | Subset of DJ; varies with the data pattern |
| **Total Jitter (TJ)** | TJ = DJ + n x RJ (where n depends on BER target) |

---

### How to Measure Jitter

1. **Time Interval Error (TIE)** measurement on an oscilloscope
2. **Eye diagram** analysis — jitter appears as horizontal eye closure
3. **Histogram** of edge timing — shows RJ (Gaussian) vs DJ (bounded) decomposition
4. **Bathtub curve** — plots BER vs sampling point to determine TJ at a target BER

---

### Keysight Solutions for Jitter Measurement

- **InfiniiVision / Infiniium Oscilloscopes** — built-in jitter analysis with EZJIT
- **N5413B Jitter Analysis Software** — advanced RJ/DJ decomposition
- **Bit Error Rate Testers (BERT)** — J-BERT series for high-speed serial jitter tolerance testing

For detailed measurement guidance, refer to [Keysight Jitter Analysis Application Note](https://www.keysight.com/us/en/assets/7018-02537/application-notes/5989-3205.pdf).
""",
        "citations": ["faq_fastpath"],
        "translations": FAQ_TRANSLATIONS["what_is_jitter"],
    },
    {
        "id": "oscilloscope_measurement",
        "match": lambda t: (
            _matches(t, {"oscilloscope"}, {"measure", "measurement", "how", "using", "data"}, 1)
            or _matches(t, {"how", "measure"}, {"oscilloscope", "scope"}, 1)
            or "osci" in t.lower() and ("meas" in t.lower() or "mess" in t.lower() or "mesti" in t.lower() or "mesur" in t.lower() or "midid" in t.lower() or "medir" in t.lower() or "mida" in t.lower())
            or "示波器" in t or "オシロスコープ" in t or "오실로스코프" in t
        ),
        "reply": """## How to Measure Data Using an Oscilloscope

An oscilloscope captures and displays voltage signals over time. Here's a step-by-step guide:

---

### 1. Basic Setup
1. **Connect the probe** — attach the probe tip to the signal point, ground clip to circuit ground
2. **Set coupling** — AC (blocks DC offset) or DC (shows full signal)
3. **Set trigger** — Edge trigger on the signal channel at approximately 50% amplitude
4. **Adjust timebase** — Set horizontal scale to see 2-3 complete cycles
5. **Adjust vertical scale** — Set to fill ~75% of the screen

### 2. Common Measurements

| Measurement | How | Typical Use |
|------------|-----|-------------|
| **Frequency** | Use Measure > Frequency or count cycles/div | Clock signals, PWM |
| **Amplitude (Vpp)** | Measure > Vpp or count vertical divisions | Signal strength |
| **Rise/Fall Time** | Measure > Rise Time (10%-90%) | Digital signal quality |
| **RMS Voltage** | Measure > Vrms | AC power, noise analysis |
| **Duty Cycle** | Measure > Duty Cycle | PWM control signals |
| **Phase** | Measure > Phase (2-channel) | Filter response, delay |

### 3. Advanced Techniques
- **FFT** — Frequency domain analysis (detect harmonics, noise sources)
- **Eye Diagram** — Serial data quality (use pattern trigger)
- **Protocol Decode** — I2C, SPI, UART, CAN bus decoding
- **Cursor Measurements** — Manual delta-time and delta-voltage

### 4. Tips for Accurate Measurements
- Use the **10x probe** setting and match it in the oscilloscope channel menu
- **Compensate your probe** before first use (adjust trimmer capacitor)
- Use **bandwidth limit** to reduce noise on low-frequency signals
- Set **acquisition mode** to High Resolution for cleaner waveforms

---

For Keysight oscilloscope user guides, visit:
https://www.keysight.com/us/en/products/oscilloscopes.html
""",
        "citations": ["faq_fastpath"],
        "translations": FAQ_TRANSLATIONS["oscilloscope_measurement"],
    },
    {
        "id": "eye_diagram_ads",
        "match": lambda t: (
            _matches(t, {"eye", "diagram"}, {"ads", "make", "create", "how"}, 1)
            or _matches(t, {"eye", "ads"}, {"diagram", "how", "create"}, 1)
            or ("ads" in t.lower() and ("eye" in t.lower() or "augen" in t.lower() or "ojo" in t.lower() or "œil" in t.lower() or "眼" in t or "アイ" in t))
        ),
        "reply": """## How to Make an Eye Diagram Using ADS (Advanced Design System)

An eye diagram in ADS is created using a transient simulation of a serial data link, then post-processing the results. Here's how:

---

### Step-by-Step Guide

#### 1. Set Up the Schematic
- Create a new schematic in your ADS workspace
- Place a **bit sequence generator** (e.g., `PseudoRandomBitSeq`) as the data source
- Add a **transmitter model** (driver buffer or IBIS model)
- Connect your **channel** (transmission line, S-parameter block, or EM model)
- Add a **receiver termination** at the far end

#### 2. Configure Transient Simulation
- Add a **Transient Simulation** controller
- Set **Stop Time** to cover at least 1000 UI (Unit Intervals)
  - Example: For 10 Gbps, UI = 100ps, so Stop Time >= 100ns
- Set **Max Time Step** to at most UI/10 (e.g., 10ps for 10 Gbps)

#### 3. Run Simulation and View Eye Diagram
1. Run the transient simulation
2. Open the **Data Display** window
3. Insert a new plot: **Signal Integrity > Eye Diagram**
4. Select the output voltage waveform
5. Set the **bit rate** (data rate) and **clock recovery** mode

#### 4. Analyze the Eye
- **Eye Height** — vertical opening (noise margin)
- **Eye Width** — horizontal opening (timing margin)
- **Jitter** — horizontal spread at crossing points
- **Mask Test** — overlay industry-standard masks (e.g., IEEE, USB, PCIe)

---

### Alternative: Statistical Eye (Channel Simulation)
For faster results without long transient simulation:
1. Use **ADS Channel Simulation** controller
2. This performs statistical convolution — produces an eye in seconds
3. Supports BER-based eye contours (e.g., 1e-12)

---

### Keysight ADS Resources
- [ADS Signal Integrity Tutorial](https://www.keysight.com/us/en/products/software/pathwave-design-software/pathwave-advanced-design-system.html)
- [Getting Started with Channel Simulation (App Note)](https://www.keysight.com/us/en/assets/7018-06748/application-notes/5992-3781.pdf)
""",
        "citations": ["faq_fastpath"],
        "translations": FAQ_TRANSLATIONS["eye_diagram_ads"],
    },
    {
        "id": "u1610a_bandwidth",
        "match": lambda t: (
            _matches(t, {"u1610a"}, {"bandwidth", "mhz", "spec", "specifications"}, 1)
            or (re.search(r"\bu1610a\b", t.lower()) and ("band" in t.lower() or "mhz" in t.lower() or "ancho" in t.lower() or "bande" in t.lower() or "带" in t or "帯" in t or "대역" in t))
        ),
        "reply": """## U1610A Bandwidth Specifications

The **Keysight U1610A Handheld Digital Oscilloscope** has a bandwidth of **100 MHz**.

---

### Key Specifications

| Parameter | Value |
|-----------|-------|
| **Bandwidth** | **100 MHz** |
| **Sample Rate** | 2 GSa/s (single channel), 1 GSa/s (dual channel) |
| **Channels** | 2 isolated channels |
| **Memory Depth** | 2 Mpts |
| **Vertical Resolution** | 8 bits |
| **Input Impedance** | 1 MΩ ∥ ~16 pF |
| **Max Input Voltage** | 300 Vrms CAT III |
| **Display** | 5.7-inch VGA TFT LCD |
| **Battery Life** | ~4 hours |
| **Weight** | 2.4 kg |

---

### Related Model

The **U1620A** is the higher-bandwidth variant at **200 MHz** with the same form factor.

| Model | Bandwidth | Sample Rate |
|-------|-----------|-------------|
| **U1610A** | 100 MHz | 2 GSa/s |
| **U1620A** | 200 MHz | 2 GSa/s |

---

**Product page:** https://www.keysight.com/us/en/products/oscilloscopes/handheld-oscilloscopes.html
**User manual:** https://www.keysight.com/us/en/assets/9018-03621/user-manuals/9018-03621.pdf
""",
        "citations": ["faq_fastpath"],
        "translations": FAQ_TRANSLATIONS["u1610a_bandwidth"],
    },
    {
        "id": "what_is_bandwidth",
        "match": lambda t: _matches(t, {"what", "bandwidth"}, {"is", "oscilloscope", "scope", "mean"}, 0),
        "reply": """## What Is Bandwidth?

In the context of oscilloscopes and test equipment, **bandwidth** is the frequency at which the instrument's response drops to **-3 dB** (approximately 70.7%) of the input signal's amplitude.

---

### Why Bandwidth Matters

- A **100 MHz oscilloscope** accurately measures signals with fundamental frequencies up to ~100 MHz
- **Rule of thumb:** Choose an oscilloscope bandwidth at least **5x** the fundamental frequency of your signal for accurate time-domain measurements
- For digital signals: bandwidth >= 5 x (1 / rise time) to preserve edge fidelity

### Bandwidth vs. Sample Rate

| Parameter | What It Measures | Units |
|-----------|-----------------|-------|
| **Bandwidth** | Highest frequency the analog front-end can pass | MHz / GHz |
| **Sample Rate** | How fast the ADC digitizes the signal | Sa/s (GSa/s) |

**Both matter:** Bandwidth limits the frequencies captured; sample rate limits how well those frequencies are reconstructed digitally (Nyquist: sample rate >= 2 x bandwidth).
""",
        "citations": ["faq_fastpath"],
        "translations": FAQ_TRANSLATIONS["what_is_bandwidth"],
    },
    # Meta: indexed documents / sources — always English, <10ms
    {
        "id": "indexed_documents_sources",
        "match": lambda t: (
            _matches(t, {"indexed"}, {"documents", "document", "source", "sources", "details", "where", "get", "from", "each"}, 0)
            or _matches(t, {"index"}, {"documents", "document", "source", "sources", "details", "where", "overview"}, 0)
            or _matches(t, {"documents", "indexed"}, set(), 0)
            or _matches(t, {"sources", "indexed"}, set(), 0)
        ),
        "reply": """## Where to Get Details of Indexed Documents by Source

Details of what is indexed and from which sources are available as follows (response in English).

---

### 1. **Elasticsearch indices (main searchable data)**

| Source / Index | Purpose | How to inspect |
|----------------|---------|----------------|
| **next_elastic_test1** (`es_data_index`) | Cases, orders, assets — from CSV/JSON snapshots | Backend config: `ES_DATA_INDEX` / `es_data_index`. Ingest: `backend/ingest_cases_to_es.py` (cases), plus any order/asset ingest scripts. |
| **next_elastic_test3** (`es_ollama_index`) | Vector index for docs from `backend/docs` (e.g. manuals, PDFs) | Config: `ES_OLLAMA_INDEX`. Ingest: `backend/ingest_docs_to_vectors.py`. |
| **asset_v2** | AEM-style asset metadata (manuals, PDFs) | Used by `elasticsearch_websearch` for manual lookups. Ingest: `backend/ingest_attachments_to_es.py` if applicable. |
| **keysight-vectors** | BGE-M3 vector index (if used) | Config: `ES_VECTOR_INDEX`. Created on first semantic search. |

---

### 2. **Ingest scripts (what gets indexed)**

- **`backend/ingest_cases_to_es.py`** — Cases from `backend/docs/Caseextract.csv` (and related CSVs) into the data index.
- **`backend/ingest_docs_to_vectors.py`** — Documents from `backend/docs` into the Ollama vector index.
- **`backend/ingest_attachments_to_es.py`** — Attachments/assets into the configured Elasticsearch index.

Run from repo root: `cd backend && PYTHONPATH=. python ingest_<name>.py`

---

### 3. **Live / API sources (not pre-indexed)**

- **Salesforce** — Cases, orders, accounts via OAuth2 and Data API. No separate “index”; queried in real time by the agent (see `app/tools/salesforce_tool.py`).
- **Confluence** — Knowledge articles via Confluence API; searched at query time (see `app/tools/confluence_tool.py`).

---

### 4. **Single place to see config and indices**

- **Backend config:** `backend/app/config.py` — `es_data_index`, `es_ollama_index`, `es_vector_index`, `es_host`.
- **Project README:** `README.md` — setup and Elasticsearch index usage.
- **Index stats:** Use Elasticsearch API, e.g. `GET /_cat/indices?v` or `GET /next_elastic_test1/_count`, against your `ES_HOST`.

For document-level details (e.g. which PDFs or cases are in an index), query the index via the backend tools or the ingest scripts’ source files (`backend/docs/`, CSV column names in the ingest code).
""",
        "citations": ["faq_fastpath"],
        "force_english": True,
    },
]


# ── Public API ──────────────────────────────────────────────

_LANG_INTRO: dict[str, str] = {
    "de": "*(Antwort aus vorberechneter Wissensdatenbank)*\n\n",
    "es": "*(Respuesta de la base de conocimientos precalculada)*\n\n",
    "fr": "*(Réponse de la base de connaissances précalculée)*\n\n",
    "zh": "*(来自预计算知识库的回答)*\n\n",
    "zh-hans": "*(来自预计算知识库的回答)*\n\n",
    "ja": "*(事前計算済み知識ベースからの回答)*\n\n",
    "ko": "*(사전 계산된 지식 베이스의 답변)*\n\n",
}


def try_faq_fastpath(message: str, language: Optional[str] = None) -> Optional[Tuple[str, List[str]]]:
    """
    Check if the user message matches a precomputed FAQ answer.
    Returns (reply_text, citations_list) or None.

    If a language is provided and the entry has a 'translations' dict,
    the localized reply is returned prefixed with a note.
    Fallback: English reply with a language intro note prepended.
    """
    if not message or len(message) < 5:
        return None

    text = message.strip()
    lang = (language or "en").strip().lower()

    for entry in _FAQ_ENTRIES:
        try:
            if entry["match"](text):
                reply = entry["reply"]
                # Meta/technical answers (e.g. indexed documents) always in English
                if entry.get("force_english"):
                    return (reply, entry["citations"])
                # Check for pre-translated version
                translations = entry.get("translations", {})
                localized = translations.get(lang)
                if not localized:
                    # Try prefix match e.g. zh-hans -> zh
                    for k, v in translations.items():
                        if lang.startswith(k):
                            localized = v
                            break

                if localized:
                    return (localized, entry["citations"])
                elif lang not in ("en", "english"):
                    # Prepend a note so the LLM caller knows to translate
                    intro = _LANG_INTRO.get(lang, "")
                    return (intro + reply, entry["citations"])
                else:
                    return (reply, entry["citations"])
        except Exception:
            continue

    return None
