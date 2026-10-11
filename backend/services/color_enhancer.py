def color_filter(enabled: bool) -> str | None:
    return 'eq=contrast=1.06:saturation=1.10:gamma=1.02' if enabled else None
