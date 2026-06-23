from pathlib import Path
import re

root = Path(r"F:\Course ML, DL, FL\Project\smartloan-ai")
src = root / "frontend" / "src"

targets = []
for p in src.rglob("*"):
    if p.suffix.lower() not in [".tsx", ".ts", ".jsx", ".js"]:
        continue
    txt = p.read_text(encoding="utf-8", errors="ignore")
    if "Apply Page" in txt or "Personal Form" in txt or "Confirm Step 1" in txt:
        targets.append(p)

if not targets:
    print("No Apply page file found.")
    raise SystemExit(1)

test_values = {
    "Said": "",
    "Kabir": "",
    "Father Name": "",
    "Mother Name": "",
    "01700000000": "",
    "017000000000": "",
    "applicant@example.com": "",
    "Dhaka, Bangladesh": "",
    "Software Developer": "",
    "60000": "",
}

property_names = [
    "firstName", "first_name",
    "lastName", "last_name",
    "fatherName", "father_name",
    "motherName", "mother_name",
    "age",
    "phone",
    "email",
    "address",
    "occupation",
    "monthlyIncome", "monthly_income",
]

for file_path in targets:
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    original = text

    backup_path = file_path.with_suffix(file_path.suffix + ".backup_before_professional_apply")
    backup_path.write_text(original, encoding="utf-8")

    # Remove hardcoded default test values.
    for old, new in test_values.items():
        text = text.replace(f'"{old}"', f'"{new}"')
        text = text.replace(f"'{old}'", f"'{new}'")
        text = text.replace(f"`{old}`", f"`{new}`")

    # Clean common object defaults.
    for name in property_names:
        text = re.sub(
            rf"({name}\s*:\s*)['\"][^'\"]*['\"]",
            rf'\1""',
            text
        )

    # Clean fallback default values like value || "Said".
    text = re.sub(r"\|\|\s*['\"](Said|Kabir|Father Name|Mother Name|01700000000|017000000000|applicant@example.com|Dhaka, Bangladesh|Software Developer|60000)['\"]", '|| ""', text)
    text = re.sub(r"\?\?\s*['\"](Said|Kabir|Father Name|Mother Name|01700000000|017000000000|applicant@example.com|Dhaka, Bangladesh|Software Developer|60000)['\"]", '?? ""', text)

    # Improve placeholders if they became empty.
    text = text.replace('placeholder=""', 'placeholder="Enter information"')

    if text != original:
        file_path.write_text(text, encoding="utf-8")
        print(f"Updated: {file_path}")
    else:
        print(f"Checked, no hardcoded defaults found: {file_path}")

print("Professional Apply Form cleanup completed.")
