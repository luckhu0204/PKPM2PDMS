# -*- coding: utf-8 -*-
"""Session helper: print head of GBK/UTF-8 text files with line numbers.
Usage: python read_gbk.py <file> [maxlines] [encoding]
"""
import sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

def main():
    if len(sys.argv) < 2:
        print("usage: read_gbk.py <file> [maxlines] [encoding]")
        return 2
    path = sys.argv[1]
    maxlines = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    enc = sys.argv[3] if len(sys.argv) > 3 else "gbk"
    with open(path, "r", encoding=enc, errors="replace") as f:
        for i, line in enumerate(f, 1):
            if i > maxlines:
                print("... (truncated at %d lines)" % maxlines)
                break
            print("%4d: %s" % (i, line.rstrip("\r\n")))
    return 0

if __name__ == "__main__":
    sys.exit(main())
