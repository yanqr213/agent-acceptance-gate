import ast


def parse_yaml_lite(text):
    """Parse a small YAML subset: mappings, lists, quoted scalars, booleans."""
    lines = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        lines.append((indent, raw.strip()))
    if not lines:
        return {}
    data, index = _parse_block(lines, 0, lines[0][0])
    if index != len(lines):
        raise ValueError("Could not parse YAML-lite document")
    return data


def _parse_block(lines, index, indent):
    if lines[index][1].startswith("- "):
        return _parse_list(lines, index, indent)
    return _parse_map(lines, index, indent)


def _parse_map(lines, index, indent):
    result = {}
    while index < len(lines):
        line_indent, content = lines[index]
        if line_indent < indent:
            break
        if line_indent > indent:
            raise ValueError("Unexpected indentation near '%s'" % content)
        if content.startswith("- "):
            break
        if ":" not in content:
            raise ValueError("Expected key/value near '%s'" % content)
        key, value = content.split(":", 1)
        key = key.strip()
        value = value.strip()
        index += 1
        if value:
            result[key] = _parse_scalar(value)
        elif index < len(lines) and lines[index][0] > line_indent:
            result[key], index = _parse_block(lines, index, lines[index][0])
        else:
            result[key] = None
    return result, index


def _parse_list(lines, index, indent):
    result = []
    while index < len(lines):
        line_indent, content = lines[index]
        if line_indent < indent:
            break
        if line_indent > indent:
            raise ValueError("Unexpected indentation near '%s'" % content)
        if not content.startswith("- "):
            break
        item = content[2:].strip()
        index += 1
        if not item:
            if index < len(lines) and lines[index][0] > line_indent:
                parsed, index = _parse_block(lines, index, lines[index][0])
                result.append(parsed)
            else:
                result.append(None)
        elif ":" in item and not item.startswith(("'", '"')):
            key, value = item.split(":", 1)
            entry = {key.strip(): _parse_scalar(value.strip()) if value.strip() else None}
            while index < len(lines) and lines[index][0] > line_indent:
                nested_indent, nested_content = lines[index]
                if nested_indent <= line_indent:
                    break
                if ":" not in nested_content:
                    raise ValueError("Expected key/value near '%s'" % nested_content)
                nested_key, nested_value = nested_content.split(":", 1)
                entry[nested_key.strip()] = _parse_scalar(nested_value.strip())
                index += 1
            result.append(entry)
        else:
            result.append(_parse_scalar(item))
    return result, index


def _parse_scalar(value):
    if value is None:
        return None
    text = value.strip()
    if text in ("true", "True"):
        return True
    if text in ("false", "False"):
        return False
    if text in ("null", "None", "~"):
        return None
    if text.startswith(('"', "'")) and text.endswith(('"', "'")):
        try:
            return ast.literal_eval(text)
        except (ValueError, SyntaxError):
            return text[1:-1]
    if text.startswith("[") and text.endswith("]"):
        try:
            return ast.literal_eval(text)
        except (ValueError, SyntaxError):
            return [item.strip() for item in text[1:-1].split(",") if item.strip()]
    return text
