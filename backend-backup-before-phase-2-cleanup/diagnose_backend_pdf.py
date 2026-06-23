from pathlib import Path
import re

root = Path("app")
main_path = Path("app/main.py")

print("========== BACKEND DIAGNOSIS ==========")

print("\n[1] main.py router include/import check:")
if main_path.exists():
    main_text = main_path.read_text(encoding="utf-8", errors="ignore")
    for idx, line in enumerate(main_text.splitlines(), start=1):
        if "fixed_pdf" in line or "include_router" in line or "applications" in line:
            print(f"main.py:{idx}: {line.strip()}")
else:
    print("ERROR: app/main.py not found")

print("\n[2] Router files:")
routers = Path("app/routers")
if routers.exists():
    for p in routers.glob("*.py"):
        print(p)
else:
    print("ERROR: app/routers not found")

print("\n[3] Search old/static PDF text and endpoints in backend:")
patterns = [
    "Generated Loan Application PDF",
    "FIXED LIVE Loan Application PDF",
    "Said Kabir",
    "Father Name",
    "01700000000",
    "generated_application",
    "generate-pdf",
    "fixed-pdf",
    "FileResponse",
    "FIXED_LIVE_APPLICATION",
]
for pattern in patterns:
    print(f"\n--- Pattern: {pattern} ---")
    found = False
    for p in root.rglob("*.py"):
        text = p.read_text(encoding="utf-8", errors="ignore")
        if pattern in text:
            found = True
            for idx, line in enumerate(text.splitlines(), start=1):
                if pattern in line:
                    print(f"{p}:{idx}: {line.strip()}")
    if not found:
        print("NOT FOUND")

print("\n[4] Fixed PDF route file preview:")
fixed_path = Path("app/routers/fixed_pdf.py")
if fixed_path.exists():
    text = fixed_path.read_text(encoding="utf-8", errors="ignore")
    print("fixed_pdf.py exists:", fixed_path.stat().st_size, "bytes")
    for idx, line in enumerate(text.splitlines(), start=1):
        if "@router" in line or "def " in line or "FIXED LIVE" in line or "FileResponse" in line:
            print(f"fixed_pdf.py:{idx}: {line.strip()}")
else:
    print("fixed_pdf.py NOT FOUND")

print("\n========== END BACKEND DIAGNOSIS ==========")
