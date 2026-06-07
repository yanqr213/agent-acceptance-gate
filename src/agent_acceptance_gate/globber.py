import fnmatch


def normalize_path(path):
    return str(path).replace("\\", "/").strip()


def matches_glob(path, pattern):
    value = normalize_path(path)
    pat = normalize_path(pattern)
    if fnmatch.fnmatch(value, pat):
        return True
    if pat.startswith("**/") and fnmatch.fnmatch(value, pat[3:]):
        return True
    return False


def any_match(path, patterns):
    return any(matches_glob(path, pattern) for pattern in patterns)
