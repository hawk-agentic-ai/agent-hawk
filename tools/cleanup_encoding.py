import os
import sys

# Patterns to strip or replace (explicit unicode escapes to remain stable)
REPLACEMENTS = {
    # Common garbled bullet/status markers
    "\uFFFDo.": "",              # 
    "\uFFFD?O": "",              # 
    "\uFFFDs\uFFFD": "",         # 
    "\uFFFDs\uFFFD\uFFFD,?": "",  # �,?

    # Garbled "dY" tokens observed in docs/logs/strings
    "": "",
    "": "",
    "": "",
    "dY\"<": "",
    "dY\"S": "",
    "dY\"^": "",
    "dY\"?": "",
    "dY\"\uFFFD": "",          # 
    "dY\u000f-": "",
}

TEXT_EXTS = {
    ".md", ".ts", ".js", ".json", ".txt", ".py", ".sql", ".sh", ".tf", ".yml", ".yaml"
}

EXCLUDE_DIRS = {"node_modules", "out-tsc", "public", "__pycache__", ".git", "docs"}

AGGRESSIVE_EXTS = {".md", ".txt", ".ts"}

def should_process(path: str) -> bool:
    if any(part in EXCLUDE_DIRS for part in path.replace("\\", "/").split("/")):
        return False
    _, ext = os.path.splitext(path)
    return ext.lower() in TEXT_EXTS

def strip_non_ascii(s: str) -> str:
    out = []
    for ch in s:
        o = ord(ch)
        if ch in ("\n", "\r", "\t"):
            out.append(ch)
        elif 32 <= o <= 126:
            out.append(ch)
        else:
            # drop non-ascii/control
            pass
    return "".join(out)

def clean_content(path: str, content: str) -> str:
    # Replace known tokens first
    for bad, good in REPLACEMENTS.items():
        if bad:
            content = content.replace(bad, good)
    # For docs/text, strip non-ascii noise
    _, ext = os.path.splitext(path)
    if ext.lower() in AGGRESSIVE_EXTS:
        content = strip_non_ascii(content)
    return content

def main(root: str):
    changed = 0
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune excluded dirs
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            if not should_process(fpath):
                continue
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                    orig = f.read()
                cleaned = clean_content(fpath, orig)
                if cleaned != orig:
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write(cleaned)
                    changed += 1
                    print(f"Cleaned: {fpath}")
            except Exception as e:
                print(f"Skip {fpath}: {e}")
    print(f"Total files modified: {changed}")

if __name__ == "__main__":
    root_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    main(root_dir)

