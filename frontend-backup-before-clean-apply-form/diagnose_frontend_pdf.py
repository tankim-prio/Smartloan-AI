from pathlib import Path
import re

root = Path("src")
app_path = Path("src/App.tsx")
main_path = Path("src/main.tsx")

print("========== FRONTEND DIAGNOSIS ==========")

if not app_path.exists():
    print("ERROR: src/App.tsx not found")
    raise SystemExit()

content = app_path.read_text(encoding="utf-8", errors="ignore")

print("\n[1] App.tsx size:")
print(app_path.stat().st_size, "bytes")

print("\n[2] TypeScript files inside src that look like backups and may break build:")
backup_files = []
for p in root.rglob("*"):
    if p.suffix.lower() in [".ts", ".tsx"] and re.search(r"backup|before|old|copy", p.name, re.I):
        backup_files.append(p)

if backup_files:
    for p in backup_files:
        print("FOUND_BACKUP_TS_FILE:", p)
else:
    print("No backup .ts/.tsx files found inside src.")

print("\n[3] main.tsx imports:")
if main_path.exists():
    main_content = main_path.read_text(encoding="utf-8", errors="ignore")
    for line in main_content.splitlines():
        if line.strip().startswith("import"):
            print(line)
else:
    print("ERROR: src/main.tsx not found")

def find_function_span(text, name):
    match = re.search(rf"function\s+{name}\s*\([^)]*\)\s*\{{", text)
    if not match:
        return None

    start = match.start()
    brace_start = text.find("{", match.end() - 1)
    depth = 0

    for i in range(brace_start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return start, i + 1

    return None

def find_arrow_function(section, name):
    match = re.search(rf"const\s+{name}\s*=\s*(?:async\s*)?\([^)]*\)\s*=>\s*\{{", section)
    if not match:
        return ""

    start = match.start()
    brace_start = section.find("{", match.end() - 1)
    depth = 0

    for i in range(brace_start, len(section)):
        if section[i] == "{":
            depth += 1
        elif section[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                while end < len(section) and section[end] in [" ", "\t", "\r", "\n"]:
                    end += 1
                if end < len(section) and section[end] == ";":
                    end += 1
                return section[start:end]

    return ""

span = find_function_span(content, "ApplyPage")

print("\n[4] ApplyPage status:")
if not span:
    print("ERROR: ApplyPage not found")
    apply_code = ""
else:
    start, end = span
    apply_code = content[start:end]
    print("ApplyPage found.")
    print("ApplyPage starts near character:", start)
    print("ApplyPage ends near character:", end)
    print("ApplyPage length:", len(apply_code))

print("\n[5] ApplyPage important variable checks:")
checks = [
    "const [stepOne",
    "const [stepTwo",
    "const applicationId",
    "application?.id",
    "buildFixedPdfPayload",
    "downloadFixedPdfFromCurrentForm",
    "generatePdf",
    "downloadGeneratedPdf",
    "/applications/${applicationId}/generate-pdf",
    "/fixed-pdf/applications",
    "Download FIXED LIVE PDF",
    "Generated Loan Application PDF",
    "FIXED LIVE Loan Application PDF",
]
for item in checks:
    print(f"{item}: ", item in apply_code)

print("\n[6] Full generatePdf function inside ApplyPage:")
generate_body = find_arrow_function(apply_code, "generatePdf")
print(generate_body if generate_body else "generatePdf not found inside ApplyPage")

print("\n[7] Full downloadGeneratedPdf function inside ApplyPage:")
download_body = find_arrow_function(apply_code, "downloadGeneratedPdf")
print(download_body if download_body else "downloadGeneratedPdf not found inside ApplyPage")

print("\n[8] Full downloadFixedPdfFromCurrentForm function inside ApplyPage:")
fixed_body = find_arrow_function(apply_code, "downloadFixedPdfFromCurrentForm")
print(fixed_body if fixed_body else "downloadFixedPdfFromCurrentForm not found inside ApplyPage")

print("\n[9] Top-level misplaced PDF helpers outside ApplyPage:")
outside = content
if span:
    outside = content[:span[0]] + content[span[1]:]

for name in ["buildFixedPdfPayload", "downloadFixedPdfFromCurrentForm", "generatePdf", "downloadGeneratedPdf"]:
    count = len(re.findall(rf"const\s+{name}\s*=", outside))
    print(f"{name} outside ApplyPage:", count)

print("\n[10] Search old/static PDF text and endpoints in src:")
patterns = [
    "Generated Loan Application PDF",
    "Said Kabir",
    "Father Name",
    "01700000000",
    "generated_application",
    "generate-pdf",
    "fixed-pdf/applications",
    "FIXED_LIVE_APPLICATION",
]
for pattern in patterns:
    print(f"\n--- Pattern: {pattern} ---")
    found = False
    for p in root.rglob("*"):
        if p.suffix.lower() not in [".ts", ".tsx", ".js", ".jsx"]:
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        if pattern in text:
            found = True
            for idx, line in enumerate(text.splitlines(), start=1):
                if pattern in line:
                    print(f"{p}:{idx}: {line.strip()}")
    if not found:
        print("NOT FOUND")

print("\n========== END FRONTEND DIAGNOSIS ==========")
