from pathlib import Path
import re

app = Path("src/App.tsx")
text = app.read_text(encoding="utf-8", errors="ignore")

print("========== FRONTEND PDF ROUTE CHECK ==========")

patterns = [
    "/applications/${applicationId}/generate-pdf",
    "/applications/",
    "generate-pdf",
    "generated_pdf",
    "fixed-pdf/applications",
    "Download FIXED LIVE PDF",
    "downloadFixedPdfFromCurrentForm",
    "generatePdf",
    "Generated Loan Application PDF",
    "Said Kabir",
    "Father Name",
    "01700000000",
]

for pattern in patterns:
    print(f"\n--- Searching: {pattern} ---")
    found = False
    for i, line in enumerate(text.splitlines(), start=1):
        if pattern in line:
            found = True
            print(f"Line {i}: {line.strip()}")
    if not found:
        print("NOT FOUND")

print("\n========== CHECK APPLY PAGE FUNCTIONS ==========")

def find_arrow_function(source, name):
    match = re.search(rf"const\s+{name}\s*=\s*async\s*\(\)\s*=>\s*\{{", source)
    if not match:
        return None

    start = match.start()
    brace_start = source.find("{", match.end() - 1)
    depth = 0

    for i in range(brace_start, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                while end < len(source) and source[end] in [" ", "\t", "\r", "\n"]:
                    end += 1
                if end < len(source) and source[end] == ";":
                    end += 1
                return source[start:end]

    return None

for fn in ["generatePdf", "downloadGeneratedPdf", "downloadFixedPdfFromCurrentForm"]:
    print(f"\n===== {fn} =====")
    body = find_arrow_function(text, fn)
    print(body if body else "NOT FOUND")

print("\n========== DIST BUILD ROUTE CHECK ==========")

dist = Path("dist/assets")
if not dist.exists():
    print("dist/assets not found. Run npm run build first.")
else:
    for js in dist.glob("*.js"):
        js_text = js.read_text(encoding="utf-8", errors="ignore")
        if any(p in js_text for p in ["generate-pdf", "fixed-pdf/applications", "Generated Loan Application PDF", "Said Kabir"]):
            print(f"\nFile: {js}")
            for pattern in ["generate-pdf", "fixed-pdf/applications", "Generated Loan Application PDF", "Said Kabir"]:
                if pattern in js_text:
                    print("FOUND IN DIST:", pattern)

print("\n========== END ==========")
