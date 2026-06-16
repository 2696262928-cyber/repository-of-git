def extract_code_like_lines(text: str) -> list[str]:
    """Extract simple code-like lines for later analysis."""
    keywords = ("def ", "class ", "import ", "#include", "public static", "SELECT ", "CREATE TABLE")
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if any(stripped.startswith(keyword) for keyword in keywords):
            lines.append(line)
    return lines
