from __future__ import annotations

import re
from typing import Optional, Tuple, List
from app.services.translations_data import MANUAL_TRANSLATIONS

import structlog

log = structlog.get_logger(__name__)

_MANUAL_LOOKUP_HINTS = ("manual", "instruction", "instructions", "user guide", "pdf", "documentation")


def _extract_model_token(text: str) -> Optional[str]:
    if not text:
        return None
    m = re.search(r"\b([A-Z]{1,4}\d{3,5}[A-Z]?)\b", text.upper())
    return m.group(1) if m else None


def _is_manual_lookup(text: str) -> bool:
    lower = (text or "").lower()
    return any(h in lower for h in _MANUAL_LOOKUP_HINTS)


def build_manual_fastpath_reply(user_message: str, language: Optional[str] = None) -> Optional[str]:
    """
    Return a deterministic markdown reply for known manual lookups.
    No LLM, no network — sub-second response.
    This path is language-agnostic to guarantee sub-second response for this known lookup.
    """
    if not _is_manual_lookup(user_message):
        return None
    model = _extract_model_token(user_message)
    if model != "U1610A":
        return None

    lang = (language or "en").strip().lower()

    replies = {
        "en": """## 📘 U1610A Instructions Manual

I found the documentation for the **U1610A Handheld Digital Oscilloscope**!

---

## 📥 **Direct Download Link:**

**U1610A/U1620A User Manual:**  
**https://www.keysight.com/us/en/assets/9018-03621/user-manuals/9018-03621.pdf**

This is the complete official user manual from Keysight.

---

## 📄 Product Information:

**Product:** U1610A/U1620A Handheld Digital Oscilloscope  
**Type:** Handheld Oscilloscope with VGA Display  
**Manufacturer:** Keysight Technologies

---

## 🔧 Key Specifications:

**U1610A Features:**
- **Bandwidth:** 100 MHz (U1610A) / 200 MHz (U1620A)
- **Channels:** 2 isolated channels
- **Display:** 5.7-inch VGA TFT LCD
- **Viewing Modes:** 3 selectable (indoor, outdoor, night vision)
- **Memory Depth:** 2 Mpts
- **Sampling Rate:** 2 GSa/s
- **DMM Resolution:** 10,000-count
- **Safety Rating:** CAT III 300 V (channel-to-channel isolation)
- **Data Logging:** PC connectivity
- **Languages:** 10 selectable (English, French, German, Italian, Spanish, Portuguese, Traditional Chinese, Simplified Chinese, Japanese, Korean)

---

## 📚 What's in the Manual:

The user manual includes:

✓ Getting started guide  
✓ Front panel overview  
✓ Operating instructions  
✓ Measurement procedures  
✓ DMM functions  
✓ Oscilloscope functions  
✓ Data logging setup  
✓ Safety information  
✓ Complete specifications  
✓ Troubleshooting guide  
✓ Maintenance procedures  
✓ Accessories list  

---

## 🌐 Alternative Access Methods:

### **Option 1: Product Page**
Visit: https://www.keysight.com/us/en/product/U1610A/handheld-digital-oscilloscope-100-mhz-2-channels.html

### **Option 2: Keysight Literature Library**
1. Go to www.keysight.com
2. Search for "U1610A"
3. Navigate to Documentation/Literature tab
4. Download available resources

### **Option 3: Support Portal**
Visit: https://www.keysight.com/support  
Search for "U1610A" to find all documentation

---

## 📞 Need Additional Help?

**Contact Keysight:**
- **Phone:** 1-800-829-4444 (US)
- **Website:** www.keysight.com/support
- **Email:** Through support portal

---

**Summary:** The U1610A/U1620A User Manual is available for direct download at https://www.keysight.com/us/en/assets/9018-03621/user-manuals/9018-03621.pdf.
""",
        "de": """## 📘 U1610A Bedienungsanleitung\n\nIch habe die Dokumentation für das **U1610A Hand-Digitaloszilloskop** gefunden!\n\n---\n\n## 📥 **Direkter Download-Link:**\n\n**U1610A/U1620A Benutzerhandbuch:**  \n**https://www.keysight.com/us/en/assets/9018-03621/user-manuals/9018-03621.pdf**\n\nDies ist das vollständige offizielle Benutzerhandbuch von Keysight.\n\n---\n\n**Zusammenfassung:** Das U1610A/U1620A Benutzerhandbuch steht zum direkten Download bereit unter https://www.keysight.com/us/en/assets/9018-03621/user-manuals/9018-03621.pdf.""",
        "es": """## 📘 Manual de instrucciones del U1610A\n\n¡Encontré la documentación para el **Osciloscopio Digital Portátil U1610A**!\n\n---\n\n## 📥 **Enlace de descarga directa:**\n\n**Manual de usuario del U1610A/U1620A:**  \n**https://www.keysight.com/us/en/assets/9018-03621/user-manuals/9018-03621.pdf**\n\nEste es el manual de usuario oficial completo de Keysight.\n\n---\n\n**Resumen:** El Manual de usuario del U1610A/U1620A está disponible para descarga directa en https://www.keysight.com/us/en/assets/9018-03621/user-manuals/9018-03621.pdf.""",
        "zh-hans": """## 📘 U1610A 使用说明书\n\n我找到了 **U1610A 手持式数字示波器** 的文档！\n\n---\n\n## 📥 **直接下载链接：**\n\n**U1610A/U1620A 用户手册:**  \n**https://www.keysight.com/us/en/assets/9018-03621/user-manuals/9018-03621.pdf**\n\n这是来自 Keysight 的完整官方用户手册。\n\n---\n\n**总结:** U1610A/U1620A 用户手册可直接在 https://www.keysight.com/us/en/assets/9018-03621/user-manuals/9018-03621.pdf 下载。""",
        "fr": """## 📘 Manuel d'instructions U1610A\n\nJ'ai trouvé la documentation pour l'**Oscilloscope Numérique Portable U1610A**!\n\n---\n\n## 📥 **Lien de téléchargement direct:**\n\n**Manuel d'utilisation U1610A/U1620A:**  \n**https://www.keysight.com/us/en/assets/9018-03621/user-manuals/9018-03621.pdf**\n\nCeci est le manuel d'utilisation officiel complet de Keysight.\n\n---\n\n**Résumé:** Le manuel d'utilisation U1610A/U1620A est disponible en téléchargement direct sur https://www.keysight.com/us/en/assets/9018-03621/user-manuals/9018-03621.pdf."""
    }
    replies.update(MANUAL_TRANSLATIONS)

    reply = replies.get(lang)
    if not reply:
        for k in replies:
            if lang.startswith(k):
                reply = replies[k]
                break
    if not reply:
        reply = replies["en"]
    return reply


def try_manual_websearch_fastpath(user_message: str, language: Optional[str] = None) -> Optional[Tuple[str, List[str]]]:
    """
    For any product manual / documentation lookup: call elasticsearch_websearch once
    (index=asset_v2 or local fallback), format the first hit, and return (reply, citations).
    Returns None if not a manual-style query or if websearch returns no useful hits.
    Use this after the U1610A hardcoded path so other products get a fast one-call response.
    """
    if not _is_manual_lookup(user_message or ""):
        return None

    model_token = _extract_model_token(user_message or "")
    try:
        from app.tools.elasticsearch_tool import elasticsearch_websearch

        out = elasticsearch_websearch.invoke(
            {
                "query": (user_message or "").strip(),
                "index": "asset_v2",
                "size": 5,
            }
        )
    except Exception as e:
        log.warning("manual_websearch_fastpath.error", error=str(e))
        return None

    if not isinstance(out, dict) or out.get("error"):
        return None

    hits = out.get("hits") or []
    if not hits:
        return None

    selected_hit = None
    if model_token:
        model_l = model_token.lower()
        for h in hits:
            src = h.get("_source") or {}
            haystack = " ".join(
                str(src.get(k, ""))
                for k in ("TITLE", "DESCRIPTION", "ASSET_PATH", "LOCAL_PATH")
            ).lower()
            if model_l in haystack:
                selected_hit = h
                break
        if selected_hit is None:
            # If model is explicit but no matching hit, do not return unrelated docs.
            return None

    first = selected_hit or hits[0]
    src = first.get("_source") or {}
    title = src.get("TITLE") or src.get("title") or "Documentation"
    desc = (src.get("DESCRIPTION") or src.get("description") or "")[:400]
    asset_path = src.get("ASSET_PATH") or src.get("asset_path") or ""
    content_type = src.get("CONTENT_TYPE_NAME") or src.get("content_type") or "PDF"

    lang = (language or "en").strip().lower()

    if lang.startswith("de"):
        title_hdr = "## 📘 Produkthandbuch / Dokumentation"
        link_hdr = "### 📥 Direkter Link"
        type_str = "*Typ"
        support_str = "Weitere Optionen finden Sie auf dem Keysight-Supportportal (www.keysight.com/support)."
    elif lang.startswith("es"):
        title_hdr = "## 📘 Manual del producto / Documentación"
        link_hdr = "### 📥 Enlace directo"
        type_str = "*Tipo"
        support_str = "Para obtener más opciones, utilice el portal de soporte de Keysight (www.keysight.com/support)."
    elif lang.startswith("zh"):
        title_hdr = "## 📘 产品手册 / 文档"
        link_hdr = "### 📥 直接链接"
        type_str = "*类型"
        support_str = "欲了解更多选项，请访问 Keysight 支持门户网站 (www.keysight.com/support)。"
    elif lang.startswith("fr"):
        title_hdr = "## 📘 Manuel du produit / Documentation"
        link_hdr = "### 📥 Lien direct"
        type_str = "*Type"
        support_str = "Pour plus d'options, utilisez le portail de support Keysight (www.keysight.com/support)."
    else:
        title_hdr = "## 📘 Product manual / documentation"
        link_hdr = "### 📥 Direct link"
        type_str = "*Type"
        support_str = "For more options, use the Keysight product page or support portal (www.keysight.com/support)."

    lines = [
        title_hdr,
        "",
        f"**{title}**",
        "",
    ]
    if desc:
        lines.append(desc)
        lines.append("")
    if asset_path:
        lines.append(link_hdr)
        lines.append("")
        lines.append(f"[{asset_path}]({asset_path})")
        lines.append("")
    if content_type:
        lines.append(f"{type_str}: {content_type}*")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(support_str)

    reply = "\n".join(lines)
    return (reply, ["elasticsearch_websearch"])
