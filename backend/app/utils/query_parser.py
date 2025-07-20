import re
from unidecode import unidecode

# نسخه قدرتمندتر و هوشمندتر استخراج فیلتر از پرسش کاربر

def extract_keywords(user_input: str) -> dict:
    user_input = unidecode(user_input.strip().lower())

    features = []
    brand = None
    size_prefs = []
    category = None
    budget_min = None
    budget_max = None

    # -------------------- برند --------------------
    known_brands = [
        "shoei", "ls2", "agv", "scorpion", "hjc", "nolan",
        "shark", "icon", "airoh", "mt", "bell", "x-lite"
    ]
    for b in known_brands:
        if b in user_input:
            brand = b
            break

    # -------------------- ویژگی‌ها --------------------
    feature_keywords = [
        "zede ab", "zede-aab", "ayrodynamic", "sabok", "sabet", "tafhie", "jazzb zarbeh",
        "did vasie", "kaf poshti", "tahkiye gardan", "vasle airpods", "ba vizor"
    ]
    for feat in feature_keywords:
        if feat in user_input:
            features.append(feat)

    # -------------------- سایز --------------------
    size_keywords = ['xs', 's', 'm', 'l', 'xl', 'xxl', 'xxxl']
    for s in size_keywords:
        if re.search(r'\b' + re.escape(s) + r'\b', user_input):
            size_prefs.append(s.upper())

    # -------------------- دسته‌بندی --------------------
    category_keywords = {
        "kalaha": "کلاه کاسکت",
        "kask": "کلاه کاسکت",
        "kapshan": "پوشاک موتورسواری",
        "poushak": "پوشاک موتورسواری",
        "latik": "لاستیک موتور سیکلت",
        "protection": "پروتکشن موتور سیکلت",
        "box": "باکس موتور سیکلت",
        "lavazem": "لوازم جانبی موتورسیکلت"
    }
    for key, val in category_keywords.items():
        if key in user_input:
            category = val
            break

    # -------------------- بودجه --------------------
    # الگوهایی مثل "زیر ۳ میلیون"، "حداکثر ۵ تومن"، "تا ۴ میلیون"
    price_patterns = [
        (r'zir\s*(\d+(?:\.\d+)?)\s*(m|t|million|toman)', 'max'),
        (r'ta\s*(\d+(?:\.\d+)?)\s*(m|t|million|toman)', 'max'),
        (r'hadaksar\s*(\d+(?:\.\d+)?)\s*(m|t|million|toman)', 'max'),
        (r'az\s*(\d+(?:\.\d+)?)\s*(m|t|million|toman)', 'min'),
        (r'dar baze\s*(\d+(?:\.\d+)?)\s*ta\s*(\d+(?:\.\d+)?)\s*(m|t|million|toman)', 'range')
    ]

    for pattern, kind in price_patterns:
        match = re.search(pattern, user_input)
        if match:
            if kind == 'max':
                num = float(match.group(1))
                budget_max = int(num * 1_000_000)
            elif kind == 'min':
                num = float(match.group(1))
                budget_min = int(num * 1_000_000)
            elif kind == 'range':
                budget_min = int(float(match.group(1)) * 1_000_000)
                budget_max = int(float(match.group(2)) * 1_000_000)
            break

    return {
        "brand": brand,
        "feature_keywords": features or None,
        "size_preferences": size_prefs or None,
        "query_category": category,
        "price_min": budget_min,
        "price_max": budget_max
    }