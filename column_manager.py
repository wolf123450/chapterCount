"""
Manages the two custom columns and applies the overwrite policy.

Column lookup names are read from config so users can rename them.
Calibre DB is passed in (not imported) to keep this module testable via DI.
"""


_COLUMN_DEFS = {
    'count': {
        'label_key':   'count_column',
        'name':        'Chapter Count',
        'datatype':    'int',
        'is_multiple': None,
        'editable':    True,
        'display':     {},
    },
    'method': {
        'label_key':   'method_column',
        'name':        'Chapter Detection Method',
        'datatype':    'text',
        'is_multiple': None,
        'editable':    True,
        'display':     {},
    },
}


def ensure_columns(db, prefs: dict) -> None:
    """Create missing custom columns. Call on plugin init and before every write."""
    existing = {col['label'] for col in db.custom_column_list()}
    for key, defn in _COLUMN_DEFS.items():
        label = _bare_label(prefs.get(defn['label_key'], f"#{defn['name'].lower().replace(' ', '_')}"))
        if label not in existing:
            db.create_custom_column(
                label=label,
                name=defn['name'],
                datatype=defn['datatype'],
                is_multiple=defn['is_multiple'],
                editable=defn['editable'],
                display=defn['display'],
            )


def should_write(db, book_id: int, new_result, prefs: dict) -> bool:
    """
    Return True if the new DetectionResult should be written,
    based on the configured overwrite policy.
    """
    policy = prefs.get('overwrite_policy', 'preserve_manual')

    method_label = _bare_label(prefs.get('method_column', '#chapter_detection_method'))
    current_method = db.get_custom(book_id, label=method_label, index_is_id=True)

    if current_method is None:
        return True  # empty → always write

    if policy == 'always':
        return True
    if policy == 'never':
        return False
    # 'preserve_manual': write unless current is manual
    return 'manual' not in str(current_method)


def write_result(db, book_id: int, result, prefs: dict) -> None:
    """Write DetectionResult to both custom columns."""
    ensure_columns(db, prefs)

    count_label  = _bare_label(prefs.get('count_column',  '#chapter_count'))
    method_label = _bare_label(prefs.get('method_column', '#chapter_detection_method'))

    db.set_custom(book_id, result.count,         label=count_label,  index_is_id=True)
    db.set_custom(book_id, result.column_value(), label=method_label, index_is_id=True)


def _bare_label(col_name: str) -> str:
    """Strip leading '#' from a column lookup name."""
    return col_name.lstrip('#')
