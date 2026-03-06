from __future__ import annotations

import re
from typing import Optional, Tuple, List
from app.services.translations_data import PRODUCT_TRANSLATIONS


_SAMPLE_RATE_PATTERN = re.compile(r"\b2(?:\.0+)?\s*g\s*sa\s*/?\s*s\b", re.I)
_PRICE_PATTERN = re.compile(r"\b(price|pricing|cost|how much|usd|us)\b", re.I)


def _looks_like_product_sample_rate_query(text: str) -> bool:
    q = (text or "").lower()
    if not bool(_SAMPLE_RATE_PATTERN.search(q)):
        return False
    # "sample rate", "abtastrate", "frecuencia de muestreo", "采样率", "échantillonnage", "サンプリングレート", "샘플링 속도"
    keywords = ["sample", "abtast", "muestreo", "échantillon", "采", "采样", "サンプリング", "샘플"]
    if not any(k in q for k in keywords):
        return False
    return True


def _looks_like_dsox1202a_price_query(text: str) -> bool:
    q = (text or "").lower()
    if "dsox1202a" not in q:
        return False
    return bool(_PRICE_PATTERN.search(q))


def try_product_spec_fastpath(message: str, language: Optional[str]) -> Optional[Tuple[str, List[str]]]:
    """
    Deterministic product answer for known "2 GSa/s product" prompts.
    Keeps responses product-centric and avoids drifting to generic app notes.
    """
    if _looks_like_dsox1202a_price_query(message):
        reply = """## DSOX1202A Price (US)

**Typical US entry price:** **starting around US$997** (base configuration).

---

### Notes
- Final price depends on configuration, options, calibration, and support package.
- Distributor pricing and promotions can change.

### Product Page
https://www.keysight.com/us/en/products/oscilloscopes/infiniivision-2-4-channel-digital-oscilloscopes/infiniivision-1000-x-series-low-cost-oscilloscopes.html

### Get an Exact Quote
- Keysight Sales (US): **1-800-829-4444**
- Or request quote via: https://www.keysight.com/us/en/contact-us.html
"""
        return (reply, ["product_pricing_fastpath"])

    if not _looks_like_product_sample_rate_query(message):
        return None

    lang = (language or "en").strip().lower()
    
    replies = {
        "en": """## Products with Max Sample Rate 2 GSa/s

Yes. Keysight offers multiple products with **2 GSa/s maximum sample rate**.

---

## 🔬 Confirmed Products

### 1. U1610A/U1620A Handheld Digital Oscilloscope

- **Max Sample Rate:** 2 GSa/s
- **Bandwidth:** 100 MHz (U1610A) / 200 MHz (U1620A)
- **Channels:** 2 isolated channels
- **Memory Depth:** 2 Mpts
- **Display:** 5.7-inch VGA TFT LCD
- **Safety Rating:** CAT III 300 V

**Product Page:**  
https://www.keysight.com/us/en/products/oscilloscopes/handheld-oscilloscopes.html

**User Manual:**  
https://www.keysight.com/us/en/assets/9018-03621/user-manuals/9018-03621.pdf

---

### 2. InfiniiVision 1000 X-Series Oscilloscopes

- **Max Sample Rate:** 2 GSa/s
- **Bandwidth:** 70 MHz to 200 MHz (model dependent)
- **Channels:** 2 or 4 analog channels
- **Memory Depth:** up to 1 Mpts

**Common models:** DSOX1202A, DSOX1204A, DSOX1102A, DSOX1104A, DSOX1072A

**Product Page:**  
https://www.keysight.com/us/en/products/oscilloscopes/infiniivision-2-4-channel-digital-oscilloscopes/infiniivision-1000-x-series-low-cost-oscilloscopes.html

---

## 📊 Product Comparison

| Product | Sample Rate | Bandwidth | Channels | Form Factor |
|---------|-------------|-----------|----------|-------------|
| U1610A | 2 GSa/s | 100 MHz | 2 | Handheld |
| U1620A | 2 GSa/s | 200 MHz | 2 | Handheld |
| DSOX1202A | 2 GSa/s | 200 MHz | 2 | Benchtop |
| DSOX1204A | 2 GSa/s | 200 MHz | 4 | Benchtop |
| DSOX1102A | 2 GSa/s | 100 MHz | 2 | Benchtop |

---

## 🎯 Summary

For **2 GSa/s** requirements, choose:
1. **U1610A/U1620A** for portable field use with isolated channels.
2. **DSOX1000 X-Series** for benchtop/lab use and lower-cost entry options.
""",
        "de": """## Produkte mit maximaler Abtastrate 2 GSa/s\n\nJa. Keysight bietet mehrere Produkte mit einer **maximalen Abtastrate von 2 GSa/s** an.\n\n---\n\n## 🔬 Bestätigte Produkte\n\n### 1. U1610A/U1620A Hand-Digitaloszilloskop\n- **Max. Abtastrate:** 2 GSa/s\n- **Bandbreite:** 100 MHz (U1610A) / 200 MHz (U1620A)\n- **Kanäle:** 2 isolierte Kanäle\n- **Speichertiefe:** 2 Mpts\n\n**Produktseite:** https://www.keysight.com/us/en/products/oscilloscopes/handheld-oscilloscopes.html\n\n### 2. InfiniiVision 1000 X-Serie Oszilloskope\n- **Max. Abtastrate:** 2 GSa/s\n- **Bandbreite:** 70 MHz bis 200 MHz\n- **Kanäle:** 2 oder 4 analoge Kanäle\n\n**Gängige Modelle:** DSOX1202A, DSOX1204A, DSOX1102A\n\n---\n\n## 🎯 Zusammenfassung\nWählen Sie die **U1610A/U1620A** für den mobilen Einsatz oder die **DSOX1000 X-Serie** für den Laborgebrauch.""",
        "es": """## Productos con frecuencia de muestreo máx. de 2 GSa/s\n\nSí. Keysight ofrece múltiples productos con **frecuencia de muestreo máxima de 2 GSa/s**.\n\n---\n\n## 🔬 Productos confirmados\n\n### 1. U1610A/U1620A Osciloscopio Digital Portátil\n- **Frecuencia de muestreo máx.:** 2 GSa/s\n- **Ancho de banda:** 100 MHz (U1610A) / 200 MHz (U1620A)\n- **Canales:** 2 canales aislados\n- **Profundidad de memoria:** 2 Mpts\n\n**Página del producto:** https://www.keysight.com/us/en/products/oscilloscopes/handheld-oscilloscopes.html\n\n### 2. Osciloscopios InfiniiVision Serie 1000 X\n- **Frecuencia de muestreo máx.:** 2 GSa/s\n- **Ancho de banda:** 70 MHz a 200 MHz\n- **Canales:** 2 o 4 canales analógicos\n\n**Modelos comunes:** DSOX1202A, DSOX1204A, DSOX1102A\n\n---\n\n## 🎯 Resumen\nElija el **U1610A/U1620A** para uso portátil en campo o la **Serie DSOX1000 X** para uso en laboratorio.""",
        "zh-hans": """## 最大采样率为 2 GSa/s 的产品\n\n是的。Keysight 提供多款**最大采样率为 2 GSa/s** 的产品。\n\n---\n\n## 🔬 确认的产品\n\n### 1. U1610A/U1620A 手持式数字示波器\n- **最大采样率:** 2 GSa/s\n- **带宽:** 100 MHz (U1610A) / 200 MHz (U1620A)\n- **通道:** 2 个隔离通道\n- **存储深度:** 2 Mpts\n\n**产品页面:** https://www.keysight.com/us/en/products/oscilloscopes/handheld-oscilloscopes.html\n\n### 2. InfiniiVision 1000 X 系列示波器\n- **最大采样率:** 2 GSa/s\n- **带宽:** 70 MHz 至 200 MHz\n- **通道:** 2 或 4 个模拟通道\n\n**常见型号:** DSOX1202A, DSOX1204A, DSOX1102A\n\n---\n\n## 🎯 总结\n如果是现场便携使用，请选择 **U1610A/U1620A**；如果是实验室台式使用，请选择 **DSOX1000 X 系列**。""",
        "fr": """## Produits avec taux d'échantillonnage max 2 GSa/s\n\nOui. Keysight propose plusieurs produits avec **un taux d'échantillonnage maximal de 2 GSa/s**.\n\n---\n\n## 🔬 Produits confirmés\n\n### 1. U1610A/U1620A Oscilloscope Numérique Portable\n- **Taux d'échantillonnage max:** 2 GSa/s\n- **Bande passante:** 100 MHz (U1610A) / 200 MHz (U1620A)\n- **Canaux:** 2 canaux isolés\n- **Profondeur de mémoire:** 2 Mpts\n\n**Page produit:** https://www.keysight.com/us/en/products/oscilloscopes/handheld-oscilloscopes.html\n\n### 2. Oscilloscopes InfiniiVision Série 1000 X\n- **Taux d'échantillonnage max:** 2 GSa/s\n- **Bande passante:** 70 MHz à 200 MHz\n- **Canaux:** 2 ou 4 canaux analogiques\n\n**Modèles courants:** DSOX1202A, DSOX1204A, DSOX1102A\n\n---\n\n## 🎯 Résumé\nChoisissez le **U1610A/U1620A** pour une utilisation portable sur le terrain, ou la **Série DSOX1000 X** pour une utilisation en laboratoire."""
    }
    replies.update(PRODUCT_TRANSLATIONS)
    
    # Prefix match (e.g., zh-hans -> zh)
    reply = replies.get(lang)
    if not reply:
        for k in replies:
            if lang.startswith(k):
                reply = replies[k]
                break
    
    if not reply:
        reply = replies["en"]

    return (reply, ["product_spec_fastpath"])
