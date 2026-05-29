#!/usr/bin/env python3
"""CLI nhập SC/HR → Notes chuẩn."""
import sys

sys.path.insert(0, ".")
from modules.notes_formatter import format_notes


def _ask(prompt: str, default: str = "") -> str:
    val = input(f"{prompt}" + (f" [{default}]" if default else "") + ": ").strip()
    return val or default


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n=== Auto Notes Formatter ===\n")
    sf = _ask("SF score (AI)", "0.90")
    sf_r = _ask("SF reason", "Claim khớp nguồn")
    sc = _ask("SC score", "0.75")
    sc_r = _ask("SC reason", "Nguồn cover đúng đoạn")
    hr = _ask("HR score", "0.85")
    hr_r = _ask("HR reason", "Xác nhận nguồn bên ngoài")
    sq = _ask("SQ score (AI)", "0.90")
    sq_r = _ask("SQ reason", "Nguồn uy tín")
    txt = _ask("TXT (OK/LỖI)", "OK")
    txt_r = _ask("TXT reason", "Không có lỗi")

    block = format_notes(
        sf=sf, sf_reason=sf_r,
        sc=sc, sc_reason=sc_r,
        hr=hr, hr_reason=hr_r,
        sq=sq, sq_reason=sq_r,
        txt=txt, txt_reason=txt_r,
    )
    print("\n📋 NOTES ĐÃ FORMAT:\n")
    print(block)
    print("\n✅ Copy vào cột M\n")


if __name__ == "__main__":
    main()
