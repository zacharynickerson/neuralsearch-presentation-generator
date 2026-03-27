"""
Build multilingual slide content from customer analytics (no hard-coded Arabic).
Uses script detection; optional langdetect for Latin languages (e.g. EN vs ES).
"""

from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from langdetect import detect
    from langdetect.lang_detect_exception import LangDetectException

    _HAS_LANGDETECT = True
except ImportError:
    _HAS_LANGDETECT = False


def _script_family(ch: str) -> Optional[str]:
    o = ord(ch)
    if 0x0600 <= o <= 0x06FF:
        return "Arabic"
    if 0x0590 <= o <= 0x05FF:
        return "Hebrew"
    if 0x0400 <= o <= 0x04FF:
        return "Cyrillic"
    if 0x4E00 <= o <= 0x9FFF:
        return "CJK"
    if 0x0E00 <= o <= 0x0E7F:
        return "Thai"
    return None


def script_label_for_query(q: str) -> str:
    """Primary non-Latin script in the query, or 'Latin'."""
    for ch in q:
        fam = _script_family(ch)
        if fam:
            return fam
    return "Latin"


def is_latin_only(q: str) -> bool:
    return script_label_for_query(q) == "Latin"


def build_multilingual_payload(
    analytics_data: dict,
    is_invalid_query: Callable[[str], bool],
) -> Dict[str, Any]:
    """
    Returns keys for render: multilingual_grid_html (full inner grid), benefit_p, footnote_p, talk_track.
    """
    searches = analytics_data.get("searches", []) or []
    best_count: Dict[str, int] = {}
    for s in searches[:8000]:
        q = (s.get("search") or "").strip()
        if not q or is_invalid_query(q):
            continue
        c = int(s.get("count", 0) or 0)
        if q not in best_count or c > best_count[q]:
            best_count[q] = c

    ranked: List[Tuple[str, int]] = sorted(best_count.items(), key=lambda x: -x[1])

    non_latin_by_script: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
    latin_ranked: List[Tuple[str, int]] = []
    for q, c in ranked:
        if is_latin_only(q):
            latin_ranked.append((q, c))
        else:
            non_latin_by_script[script_label_for_query(q)].append((q, c))

    # Case A: non-Latin queries exist — compare Latin vs dominant non-Latin script
    if non_latin_by_script:
        best_script = max(
            non_latin_by_script.keys(),
            key=lambda k: sum(t[1] for t in non_latin_by_script[k]),
        )
        col2_queries = [q for q, _ in non_latin_by_script[best_script][:6]]
        col1_queries = [q for q, _ in latin_ranked[:6]]
        if not col1_queries:
            col1_queries = [q for q, _ in ranked if is_latin_only(q)][:6]
        benefit = (
            f"NeuralSearch understands 50+ languages. No separate indices. "
            f"In your data we see both Latin-script queries and {best_script}-script queries — cross-lingual matching applies when your catalog spans languages."
        )
        foot = (
            f"Keyword search struggles across scripts. NeuralSearch aligns intent across languages when your shoppers use {best_script} and Latin script in the same store."
        )
        talk = (
            "NeuralSearch is multi-lingual out of the box — 50+ languages with no configuration. "
            "Your analytics show traffic in more than one script; NeuralSearch can connect intent across languages on one index, with no separate language indices or translation layers."
        )
        return {
            "mode": "dual",
            "col1_title": "Latin-script queries (your data)",
            "col2_title": f"{best_script}-script queries (your data)",
            "col1_queries": col1_queries,
            "col2_queries": col2_queries,
            "benefit": benefit,
            "footnote": foot,
            "talk_track": talk,
        }

    # Case B: Latin only — try langdetect for EN vs other Latin languages
    if _HAS_LANGDETECT and latin_ranked:
        by_lang: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
        for q, c in latin_ranked:
            if len(q.strip()) < 4:
                continue
            try:
                lang = detect(q)
            except (LangDetectException, Exception):
                lang = "en"
            by_lang[lang].append((q, c))

        langs_by_volume = sorted(
            by_lang.keys(),
            key=lambda k: sum(t[1] for t in by_lang[k]),
            reverse=True,
        )
        if len(langs_by_volume) >= 2 and "en" in by_lang:
            other = next((L for L in langs_by_volume if L != "en"), None)
            if other and by_lang.get(other):
                en_qs = [q for q, _ in sorted(by_lang["en"], key=lambda x: -x[1])[:6]]
                o_qs = [q for q, _ in sorted(by_lang[other], key=lambda x: -x[1])[:6]]
                lang_names = {
                    "es": "Spanish",
                    "fr": "French",
                    "de": "German",
                    "it": "Italian",
                    "pt": "Portuguese",
                    "nl": "Dutch",
                    "pl": "Polish",
                }
                oname = lang_names.get(other, other.upper())
                benefit = (
                    f"NeuralSearch understands 50+ languages. Your data includes both English and {oname} queries — "
                    f"cross-lingual matching without separate indices."
                )
                foot = (
                    f"Keyword search treats languages separately. NeuralSearch connects intent across English and {oname} using the same index."
                )
                talk = (
                    f"Your shoppers search in English and {oname}. NeuralSearch handles multilingual intent on one index — no translation layer required for relevance."
                )
                return {
                    "mode": "dual",
                    "col1_title": "English queries (your data)",
                    "col2_title": f"{oname} queries (your data)",
                    "col1_queries": en_qs,
                    "col2_queries": o_qs,
                    "benefit": benefit,
                    "footnote": foot,
                    "talk_track": talk,
                }

    # Case C: single column — top Latin queries only
    top_qs = [q for q, _ in latin_ranked[:8]]
    if not top_qs:
        top_qs = [q for q, _ in ranked[:8]]
    benefit = (
        "NeuralSearch understands 50+ languages. We did not detect a second language or script "
        "in your top queries — when you grow international traffic, the same index supports cross-lingual matching."
    )
    foot = (
        "Keyword search breaks across languages. NeuralSearch is ready when your data includes multiple languages."
    )
    talk = (
        "NeuralSearch is multi-lingual out of the box. Your current top queries appear in one primary language; "
        "as you add international traffic, NeuralSearch matches intent across 50+ languages without separate indices."
    )
    return {
        "mode": "single",
        "col1_title": "Top queries (your data)",
        "col2_title": None,
        "col1_queries": top_qs[:6],
        "col2_queries": [],
        "benefit": benefit,
        "footnote": foot,
        "talk_track": talk,
    }
