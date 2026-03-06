import re

with open("backend/app/services/faq_fastpath.py", "r") as f:
    faq_content = f.read()

faq_content = faq_content.replace(
    'from typing import Optional, Tuple, List',
    'from typing import Optional, Tuple, List\nfrom app.services.translations_data import FAQ_TRANSLATIONS'
)

for faq_id in ["what_is_jitter", "oscilloscope_measurement", "eye_diagram_ads", "u1610a_bandwidth", "what_is_bandwidth"]:
    pattern = re.compile(rf'("id": "{faq_id}",\s*"match".*?\n\s*"citations": \[.*?\],\n)(\s*}})', re.DOTALL)
    replacement = rf'\1        "translations": FAQ_TRANSLATIONS["{faq_id}"],\n\2'
    faq_content = pattern.sub(replacement, faq_content)

with open("backend/app/services/faq_fastpath.py", "w") as f:
    f.write(faq_content)

with open("backend/app/services/product_fastpath.py", "r") as f:
    prod_content = f.read()

prod_content = prod_content.replace(
    'from typing import Optional, Tuple, List',
    'from typing import Optional, Tuple, List\nfrom app.services.translations_data import PRODUCT_TRANSLATIONS'
)
prod_content = prod_content.replace('    }\n    \n    # Prefix match', '    }\n    replies.update(PRODUCT_TRANSLATIONS)\n    \n    # Prefix match')

with open("backend/app/services/product_fastpath.py", "w") as f:
    f.write(prod_content)

with open("backend/app/services/manual_fastpath.py", "r") as f:
    man_content = f.read()

man_content = man_content.replace(
    'from typing import Optional, Tuple, List',
    'from typing import Optional, Tuple, List\nfrom app.services.translations_data import MANUAL_TRANSLATIONS'
)
man_content = man_content.replace('    }\n\n    reply = replies.get(lang)', '    }\n    replies.update(MANUAL_TRANSLATIONS)\n\n    reply = replies.get(lang)')

with open("backend/app/services/manual_fastpath.py", "w") as f:
    f.write(man_content)
