"""
Career timeline analyser – parses employment date ranges, identifies
gaps > 3 months, flags overlapping dates, and computes total experience.

All dates are normalised to ``(year, month)`` tuples for comparison.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

# Month name / abbreviation → number
_MONTHS: Dict[str, int] = {}
_MONTH_NAMES = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]
for _i, _name in enumerate(_MONTH_NAMES, 1):
    _MONTHS[_name] = _i
    _MONTHS[_name[:3]] = _i          # jan, feb, …

# ── Date-range regex patterns ────────────────────────────────────────
# Matches patterns like:
#   "Jan 2020 - Mar 2022", "January 2020 – Present",
#   "2020 - 2022", "2019-Present", "06/2020 - 12/2022",
#   "May 2018 – Current"

_MONTH_PAT = "|".join(_MONTH_NAMES + [n[:3] for n in _MONTH_NAMES])
_END_PAT = r"(?:present|current|now|ongoing)"

_DATE_RANGE_PATTERNS: List[re.Pattern] = [
    # "Month Year – Month Year" or "Month Year – Present"
    re.compile(
        rf"({_MONTH_PAT})\.?\s*((?:19|20)\d{{2}})\s*[-–—to]+\s*"
        rf"(?:({_MONTH_PAT})\.?\s*((?:19|20)\d{{2}})|({_END_PAT}))",
        re.IGNORECASE,
    ),
    # "MM/YYYY – MM/YYYY" or "MM/YYYY – Present"
    re.compile(
        r"(0?[1-9]|1[0-2])\s*/\s*((?:19|20)\d{2})\s*[-–—to]+\s*"
        r"(?:(0?[1-9]|1[0-2])\s*/\s*((?:19|20)\d{2})|(" + _END_PAT + r"))",
        re.IGNORECASE,
    ),
    # "YYYY – YYYY" or "YYYY – Present" (year-only, no month)
    re.compile(
        r"(?<!\d)((?:19|20)\d{2})\s*[-–—to]+\s*"
        r"(?:((?:19|20)\d{2})|(" + _END_PAT + r"))(?!\d)",
        re.IGNORECASE,
    ),
]


# =====================================================================
# Public API
# =====================================================================

def analyse_career_timeline(text: str) -> Dict[str, Any]:
    """Parse employment dates from *text* and return timeline analysis.

    Returns a dict with:
        ``roles``              – list of ``{title, company, start, end}``
        ``gaps``               – list of ``{after_role, before_role, months}``
        ``overlaps``           – list of ``{role_a, role_b, months}``
        ``total_experience_years`` – float
        ``earliest_start``     – ``"YYYY-MM"`` or ``None``
        ``latest_end``         – ``"YYYY-MM"`` or ``None``
    """
    roles = _extract_roles(text)
    if not roles:
        return {
            "roles": [],
            "gaps": [],
            "overlaps": [],
            "total_experience_years": 0.0,
            "earliest_start": None,
            "latest_end": None,
        }

    # Sort by start date
    roles.sort(key=lambda r: r["start_tuple"])

    gaps = _find_gaps(roles, min_months=3)
    overlaps = _find_overlaps(roles)
    total_years = _total_experience(roles)

    earliest = _fmt(roles[0]["start_tuple"])
    latest = _fmt(max(r["end_tuple"] for r in roles))

    # Build serialisable output (strip internal tuples)
    clean_roles = [
        {
            "title": r["title"],
            "company": r["company"],
            "start": _fmt(r["start_tuple"]),
            "end": _fmt(r["end_tuple"]),
        }
        for r in roles
    ]

    return {
        "roles": clean_roles,
        "gaps": gaps,
        "overlaps": overlaps,
        "total_experience_years": round(total_years, 1),
        "earliest_start": earliest,
        "latest_end": latest,
    }


# ── Role extraction ─────────────────────────────────────────────────

def _extract_roles(text: str) -> List[Dict[str, Any]]:
    """Extract employment roles with parsed start/end tuples."""
    today = (date.today().year, date.today().month)

    # First pass: find all date ranges in the text
    date_ranges: List[Tuple[int, Tuple[int, int], Tuple[int, int], str]] = []

    for pat in _DATE_RANGE_PATTERNS:
        for m in pat.finditer(text):
            groups = m.groups()
            start_t, end_t = _parse_groups(groups, pat, today)
            if start_t and end_t and start_t <= end_t:
                date_ranges.append((m.start(), start_t, end_t, m.group()))

    if not date_ranges:
        return []

    # Deduplicate overlapping regex matches at the same text position
    date_ranges.sort(key=lambda x: x[0])
    deduped: List[Tuple[int, Tuple[int, int], Tuple[int, int], str]] = []
    for dr in date_ranges:
        if deduped and abs(dr[0] - deduped[-1][0]) < 5:
            # Keep the one with more specific dates (has month info)
            if dr[1][1] != 1 or dr[2][1] != 1:
                deduped[-1] = dr
            continue
        deduped.append(dr)

    # Second pass: attach title/company context from surrounding text
    roles: List[Dict[str, Any]] = []
    lines = text.split("\n")

    for pos, start_t, end_t, raw_match in deduped:
        # Find the line containing this date range
        title, company = _extract_role_context(text, pos, lines)
        roles.append({
            "title": title,
            "company": company,
            "start_tuple": start_t,
            "end_tuple": end_t,
        })

    return roles


def _parse_groups(
    groups: tuple,
    pat: re.Pattern,
    today: Tuple[int, int],
) -> Tuple[Optional[Tuple[int, int]], Optional[Tuple[int, int]]]:
    """Parse regex groups into ``(start_ym, end_ym)`` tuples."""
    try:
        if len(groups) == 5:
            # Month-name or MM/ pattern
            start_m = _parse_month(groups[0])
            start_y = int(groups[1])
            if groups[4]:  # "Present"
                end_y, end_m = today
            else:
                end_m = _parse_month(groups[2])
                end_y = int(groups[3])
            return (start_y, start_m), (end_y, end_m)
        elif len(groups) == 3:
            # Year-only pattern
            start_y = int(groups[0])
            if groups[2]:  # "Present"
                end_y, end_m = today
                return (start_y, 1), (end_y, end_m)
            else:
                end_y = int(groups[1])
                return (start_y, 1), (end_y, 12)
    except (ValueError, TypeError):
        pass
    return None, None


def _parse_month(val: Optional[str]) -> int:
    """Convert a month string to 1-12."""
    if not val:
        return 1
    val = val.strip().lower().rstrip(".")
    if val in _MONTHS:
        return _MONTHS[val]
    try:
        m = int(val)
        return m if 1 <= m <= 12 else 1
    except ValueError:
        return 1


def _extract_role_context(
    text: str, match_pos: int, lines: List[str],
) -> Tuple[str, str]:
    """Extract job title and company from the text near *match_pos*."""
    # Find which line contains the match
    char_count = 0
    match_line_idx = 0
    for i, line in enumerate(lines):
        char_count += len(line) + 1  # +1 for \n
        if char_count > match_pos:
            match_line_idx = i
            break

    # The date is often on the same line as the title, or on the line below it.
    # Try the current line first (title – company (dates) on one line),
    # then look at the line above (title – company \n dates).
    candidates = []
    if match_line_idx < len(lines):
        candidates.append(lines[match_line_idx].strip())
    if match_line_idx > 0:
        candidates.insert(0, lines[match_line_idx - 1].strip())

    title = ""
    company = ""

    for cand in candidates:
        # Strip date fragments so we can see the role info
        cleaned = re.sub(
            r"(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\.?\s*)?"
            r"(?:19|20)\d{2}\s*[-–—to]*\s*"
            r"(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\.?\s*)?"
            r"(?:(?:19|20)\d{2}|present|current|now|ongoing)?",
            "", cand, flags=re.IGNORECASE,
        ).strip()
        cleaned = re.sub(r"[(\)\s\-–—]+$", "", cleaned).strip()

        if not cleaned or len(cleaned) < 4:
            continue

        # Pattern: "Title – Company" or "Title at Company" or "Title | Company"
        role_pat = re.match(
            r"^([A-Za-z][\w\s,/]{3,50}?)\s*[-–—@|]\s*([A-Za-z][\w\s.&,]{2,50})",
            cleaned,
        )
        if role_pat:
            title = role_pat.group(1).strip()
            company = role_pat.group(2).strip()
            break

        # Fallback: use the whole cleaned line as title
        if not title:
            title = cleaned[:60]
            # Don't break — keep looking for a better match

    return title, company


# ── Gap detection ────────────────────────────────────────────────────

def _find_gaps(
    roles: List[Dict[str, Any]], min_months: int = 3,
) -> List[Dict[str, Any]]:
    """Find gaps > *min_months* between consecutive roles."""
    gaps: List[Dict[str, Any]] = []
    for i in range(len(roles) - 1):
        end_prev = roles[i]["end_tuple"]
        start_next = roles[i + 1]["start_tuple"]
        gap_months = _month_diff(end_prev, start_next)
        if gap_months > min_months:
            gaps.append({
                "after_role": roles[i].get("title", ""),
                "before_role": roles[i + 1].get("title", ""),
                "gap_months": gap_months,
                "from": _fmt(end_prev),
                "to": _fmt(start_next),
            })
    return gaps


# ── Overlap detection ────────────────────────────────────────────────

def _find_overlaps(roles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flag pairs of roles whose date ranges overlap."""
    overlaps: List[Dict[str, Any]] = []
    for i in range(len(roles)):
        for j in range(i + 1, len(roles)):
            a_start, a_end = roles[i]["start_tuple"], roles[i]["end_tuple"]
            b_start, b_end = roles[j]["start_tuple"], roles[j]["end_tuple"]
            # Overlap exists when a starts before b ends AND b starts before a ends
            if a_start < b_end and b_start < a_end:
                overlap_start = max(a_start, b_start)
                overlap_end = min(a_end, b_end)
                overlap_months = _month_diff(overlap_start, overlap_end)
                if overlap_months > 0:
                    overlaps.append({
                        "role_a": roles[i].get("title", ""),
                        "role_b": roles[j].get("title", ""),
                        "overlap_months": overlap_months,
                    })
    return overlaps


# ── Total experience ─────────────────────────────────────────────────

def _total_experience(roles: List[Dict[str, Any]]) -> float:
    """Calculate total years of experience, merging overlapping periods."""
    if not roles:
        return 0.0

    # Build list of (start, end) intervals, then merge
    intervals = [(r["start_tuple"], r["end_tuple"]) for r in roles]
    intervals.sort()

    merged: List[Tuple[Tuple[int, int], Tuple[int, int]]] = [intervals[0]]
    for start, end in intervals[1:]:
        prev_start, prev_end = merged[-1]
        if start <= prev_end:
            # Overlapping or adjacent — extend
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))

    total_months = sum(_month_diff(s, e) for s, e in merged)
    return total_months / 12.0


# ── Helpers ──────────────────────────────────────────────────────────

def _month_diff(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    """Return months from *a* to *b* (positive when b > a)."""
    return (b[0] - a[0]) * 12 + (b[1] - a[1])


def _fmt(ym: Tuple[int, int]) -> str:
    """Format ``(year, month)`` as ``'YYYY-MM'``."""
    return f"{ym[0]}-{ym[1]:02d}"
