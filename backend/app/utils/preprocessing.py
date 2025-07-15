import re
from unidecode import unidecode

# ---------------------------------------------
# preprocessing.py
# Utility functions to normalize user input and
# extract structured filters for QueryKnowledgeBaseTool
# ---------------------------------------------

def normalize_text(text: str) -> str:
    """
    Normalize Persian text:
     - Strip whitespace
     - Unify characters (ك -> ک, ي -> ی, etc.)
     - Remove diacritics via unidecode
    """
    text = text.strip()
    replacements = {
        'ك': 'ک',
        'ي': 'ی',
        'ؤ': 'و',
        'أ': 'ا',
        'ۀ': 'ه',
        'ئ': 'ی',
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    # Convert to ASCII fallback for any diacritics
    text = unidecode(text)
    return text

def extract_filters(text: str) -> dict:
    """
    Extract structured filter parameters from user query:
     - query_input: raw text
     - query_category: detected product category
     - brand: detected brand name
     - price_min / price_max: numeric price range
     - size_preferences: list of sizes (e.g. ['L','XL'])
     - feature_keywords: list of keywords after 'ویژگی'
    """
    norm = normalize_text(text).lower()
    filters = {
        'query_input': text,
        'query_category': None,
        'brand': None,
        'price_min': None,
        'price_max': None,
        'size_preferences': [],
        'feature_keywords': []
    }

    # 1. Detect category
    categories = [
        'کلاه کاسکت', 'پوشاک موتورسواری', 'لاستیک موتور سیکلت',
        'لوازم جانبی موتورسیکلت', 'پروتکشن موتور سیکلت', 'باکس موتور سیکلت'
    ]
    for cat in categories:
        if cat in text:
            filters['query_category'] = cat
            break

    # 2. Detect price expressions
    m = re.search(r"(\d[\d,]*)\s*(تومان|تومن|ت)\b", text)
    if m:
        price = int(m.group(1).replace(',', ''))
        filters['price_min'] = price
        filters['price_max'] = price
    # Price range in millions: e.g. '۵-۱۰ میلیون'
    m2 = re.search(r"(\d+)\s*[-–تاto]+\s*(\d+)\s*میلیون", norm)
    if m2:
        filters['price_min'] = int(m2.group(1)) * 1_000_000
        filters['price_max'] = int(m2.group(2)) * 1_000_000

    # 3. Detect sizes
    sizes = re.findall(r"\b(XS|S|M|L|XL|XXL|XXXL|YS|YM|YL)\b", text)
    if sizes:
        filters['size_preferences'] = [s.upper() for s in sizes]

    # 4. Extract feature keywords after 'ویژگی'
    if 'ویژگی' in text:
        feats = re.findall(r"ویژگی(?:‌ها)?[:\-]?\s*([^\n،\.]+)", text)
        if feats:
            parts = re.split(r'[،,و]', feats[0])
            filters['feature_keywords'] = [p.strip() for p in parts if p.strip()]

    # 5. Detect brand heuristically: English capitalized words
    brands = re.findall(r"\b([A-Z][a-z0-9]{1,})\b", text)
    if brands:
        filters['brand'] = brands[0]

    return filters
