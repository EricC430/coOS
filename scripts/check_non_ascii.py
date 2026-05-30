#!/usr/bin/env python3
import sys
from pathlib import Path

def check_file_ascii(file_path: Path) -> bool:
    try:
        content = file_path.read_text(encoding="utf-8")
        non_ascii = [(i, char) for i, char in enumerate(content) if ord(char) > 127]
        if non_ascii:
            print(f"[ERROR] {file_path} contains non-ASCII characters:")
            for pos, char in non_ascii[:10]:
                print(f"  - position {pos}: {repr(char)} (code: {ord(char)})")
            if len(non_ascii) > 10:
                print(f"  - ... and {len(non_ascii) - 10} more characters.")
            return False
        return True
    except Exception as e:
        print(f"[ERROR] Failed to read {file_path}: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python check_non_ascii.py <file1> <file2> ...")
        sys.exit(1)
        
    has_errors = False
    for path_str in sys.argv[1:]:
        path = Path(path_str)
        if not path.exists():
            print(f"[WARNING] File not found: {path}")
            continue
        if path.is_dir():
            for child in path.rglob("*"):
                if child.is_file() and child.suffix in [".ini", ".toml", ".py", ".env", ".example", ".json"]:
                    if not check_file_ascii(child):
                        has_errors = True
        else:
            if not check_file_ascii(path):
                has_errors = True
                
    if has_errors:
        sys.exit(1)
    else:
        print("[OK] All checked files are pure ASCII.")
        sys.exit(0)

if __name__ == "__main__":
    main()
