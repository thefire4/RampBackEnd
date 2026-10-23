"""BOM column aliases aligned with frontend material field names."""

from __future__ import annotations

import re
from typing import Optional

# Canonical field -> header text variants (normalized before match).
BOM_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "name": (
        "item",
        "symbol",
        "symbol match to bom",
        "component",
        "part",
        "material name",
    ),
    "location": (
        "location",
        "position",
        "placement",
    ),
    "material": (
        "product description",
        "description",
        "content",
        "fabric",
        "trims",
        "thread",
        "spec",
        "material",
    ),
    "article_no": (
        "product code",
        "article no",
        "article no.",
        "article",
        "code",
        "sku",
    ),
    "material_size": (
        "size",
        "size ",
        "dimensions",
    ),
    "quantity": (
        "quantity",
        "qty",
        "usage",
        "consumption",
    ),
    "supplier": (
        "supplier name",
        "supplier",
        "vendor",
    ),
    "supplier_contact": (
        "supplier contact",
        "contact",
    ),
    "uom": (
        "uom",
        "unit",
        "units",
    ),
    "color": (
        "color",
        "colour",
    ),
    "notes": (
        "notes",
        "note",
        "comments",
    ),
    "category": (
        "category",
        "type",
        "section",
    ),
    "yield": (
        "yield",
    ),
    "measurement": (
        "measurement",
        "meas",
    ),
}

KNOWN_BOM_FIELDS = set(BOM_FIELD_ALIASES.keys())

PROJECT_DETAIL_LABELS: dict[str, tuple[str, ...]] = {
    "style_no": ("style no", "style no.", "style #", "style number"),
    "po_no": ("po no", "po no.", "po#", "po #", "po"),
    "customer": ("customer", "division", "brand"),
    "size_range": ("size range",),
    "season": ("season",),
    "fabric_yarn": ("fabric/yarn", "fabric", "fabric yarn", "yarn"),
    "designer": ("manufacturer", "vendor", "designer"),
    "weight": ("weight",),
    "description": ("description", "style name", "style description"),
    "project_date": ("date",),
}

SIZE_HEADER_PATTERN = re.compile(
    r"^(XXS|XS|S|M|L|XL|XXL|XXXL|2XL|3XL|4XL|OS|ONE SIZE)$",
    re.IGNORECASE,
)

PO_COLUMN_PATTERN = re.compile(r"^po\s*\d", re.IGNORECASE)


def normalize_header(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\n", " ").strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def match_bom_field(header: str) -> Optional[str]:
    normalized = normalize_header(header)
    if not normalized:
        return None

    for field, aliases in BOM_FIELD_ALIASES.items():
        if normalized in aliases:
            return field

    best_field: Optional[str] = None
    best_len = 0
    for field, aliases in BOM_FIELD_ALIASES.items():
        for alias in aliases:
            if alias in normalized or normalized in alias:
                if len(alias) > best_len:
                    best_len = len(alias)
                    best_field = field
    return best_field


def is_size_column(header: object) -> bool:
    text = normalize_header(header).upper()
    if not text:
        return False
    if PO_COLUMN_PATTERN.match(text):
        return False
    return bool(SIZE_HEADER_PATTERN.match(text))


def is_colorway_column(header: object, mapped_field: Optional[str]) -> bool:
    if mapped_field:
        return False
    text = normalize_header(header)
    if not text or text in {"colorways", "colorway"}:
        return False
    if match_bom_field(header):
        return False
    if is_size_column(header):
        return False
    skip = {
        "sample",
        "status",
        "sketch",
        "grade",
        "note",
        "tol +/-",
        "tol",
        "ref",
        "points measured",
    }
    if text in skip:
        return False
    # Colorway headers are short-ish labels (e.g. BLACK, Dark Olive).
    return len(text) <= 40
