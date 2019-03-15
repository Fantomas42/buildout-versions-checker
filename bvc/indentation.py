"""Indentation for Buildout Versions Checker"""


def perfect_indentation(keys, rounding=4):
    """
    Find perfect indentation by iterating over keys.
    """
    max_key_length = max(len(k) for k in keys)
    indentation = max_key_length + (
        rounding - (max_key_length % rounding)
    )

    return indentation
