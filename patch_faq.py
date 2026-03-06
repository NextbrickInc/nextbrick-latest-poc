import re

with open("backend/app/services/faq_fastpath.py", "r") as f:
    content = f.read()

# Replace what_is_jitter
content = content.replace(
    'lambda t: _matches(t, {"what", "jitter"}, {"is", "define", "definition", "meaning"}, 0)',
    'lambda t: _matches(t, {"what", "jitter"}, {"is", "define", "definition", "meaning"}, 0) or "jitter" in t.lower() or "지터" in t or "抖动" in t or "ジッタ" in t'
)

# Replace oscilloscope_measurement
content = content.replace(
    'lambda t: (\n            _matches(t, {"oscilloscope"}, {"measure", "measurement", "how", "using", "data"}, 1)\n            or _matches(t, {"how", "measure"}, {"oscilloscope", "scope"}, 1)\n        )',
    'lambda t: (\n            _matches(t, {"oscilloscope"}, {"measure", "measurement", "how", "using", "data"}, 1)\n            or _matches(t, {"how", "measure"}, {"oscilloscope", "scope"}, 1)\n            or "osci" in t.lower() and ("meas" in t.lower() or "mess" in t.lower() or "mesti" in t.lower() or "mesur" in t.lower() or "midid" in t.lower() or "medir" in t.lower() or "mida" in t.lower())\n            or "示波器" in t or "オシロスコープ" in t or "오실로스코프" in t\n        )'
)

# Replace eye_diagram_ads 
content = content.replace(
    'lambda t: (\n            _matches(t, {"eye", "diagram"}, {"ads", "make", "create", "how"}, 1)\n            or _matches(t, {"eye", "ads"}, {"diagram", "how", "create"}, 1)\n        )',
    'lambda t: (\n            _matches(t, {"eye", "diagram"}, {"ads", "make", "create", "how"}, 1)\n            or _matches(t, {"eye", "ads"}, {"diagram", "how", "create"}, 1)\n            or ("ads" in t.lower() and ("eye" in t.lower() or "augen" in t.lower() or "ojo" in t.lower() or "œil" in t.lower() or "眼" in t or "アイ" in t))\n        )'
)

# Replace u1610a_bandwidth
content = content.replace(
    'lambda t: (\n            _matches(t, {"u1610a"}, {"bandwidth", "mhz", "spec", "specifications"}, 1)\n            or (re.search(r"\\bu1610a\\b", t.lower()) and _matches(t, set(), {"bandwidth", "mhz", "how", "many", "spec"}, 1))\n        )',
    'lambda t: (\n            _matches(t, {"u1610a"}, {"bandwidth", "mhz", "spec", "specifications"}, 1)\n            or (re.search(r"\\bu1610a\\b", t.lower()) and ("band" in t.lower() or "mhz" in t.lower() or "ancho" in t.lower() or "bande" in t.lower() or "带" in t or "帯" in t or "대역" in t))\n        )'
)

# Replace product_spec_fastpath in product_fastpath.py
# Wait, product_fastpath.py has _looks_like_product_sample_rate_query
# I'll just write a new script for that.

with open("backend/app/services/faq_fastpath.py", "w") as f:
    f.write(content)
