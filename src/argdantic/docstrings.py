import re

_SECTION_HEADER = re.compile(r"^(\w[\w ]*):\s*$")
_PARAM_LINE = re.compile(r"^(\*{0,2}\w+)(?:\s*\(.*\))?:\s*(.*)$")


def parse_docstring(doc: str) -> tuple[str, dict[str, str]]:
    """
    Return the first line of `doc` and a map from parameter name to its `Args:` description.

    `doc` is expected to be already dedented (as returned by `inspect.getdoc`). Continuation lines of a
    parameter, indented deeper than its name, are joined to it with single spaces.
    """
    lines = doc.splitlines()
    summary = lines[0].strip() if lines else ""
    description_parts: dict[str, list[str]] = {}
    in_args_section = False
    param_indent: int | None = None
    current_param: str | None = None
    for line in lines[1:]:
        text = line.strip()
        indent = len(line) - len(line.lstrip())
        if indent == 0 and text:
            header = _SECTION_HEADER.match(text)
            in_args_section = header is not None and header.group(1).strip() in ("Args", "Arguments")
            param_indent, current_param = None, None
            continue
        if not in_args_section or not text:
            continue
        if param_indent is None:
            param_indent = indent
        param_match = _PARAM_LINE.match(text)
        if indent == param_indent and param_match:
            param_name: str = param_match.group(1).lstrip("*")
            first_part: str = param_match.group(2)
            description_parts[param_name] = [first_part] if first_part else []
            current_param = param_name
        elif indent > param_indent and current_param is not None:
            description_parts[current_param].append(text)
    return summary, {name: " ".join(parts) for name, parts in description_parts.items()}
