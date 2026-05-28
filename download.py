import os
import re
import requests
from concurrent.futures import ThreadPoolExecutor

# =========================
# اختيار اللغة
# =========================
print("1 - عربي")
print("2 - English")

lang_choice = input("\nاختر اللغة / Choose language: ").strip()

AR = lang_choice != "2"

TXT = {
    "enter_url":
        "حط رابط archive.org: "
        if AR else
        "Enter archive.org URL: ",

    "formats":
        "\nالصيغ المتوفرة:\n"
        if AR else
        "\nAvailable formats:\n",

    "invalid":
        "ما اخترت صيغة صحيحة"
        if AR else
        "Invalid format selection",

    "selected":
        "\nالصيغ المختارة:"
        if AR else
        "\nSelected formats:",

    "folder":
        "\n📂 المجلد:"
        if AR else
        "\n📂 Folder:",

    "files":
        "⬇️ الملفات:"
        if AR else
        "⬇️ Files:",

    "downloading":
        "جاري تحميل:"
        if AR else
        "Downloading:",

    "skip":
        "تخطي:"
        if AR else
        "Skip:",

    "done":
        "\nاكتمل ✔"
        if AR else
        "\nDone ✔",
}

# =========================
# إدخال الرابط
# =========================
url_input = input(TXT["enter_url"]).strip()

# =========================
# عدد التحميلات المتزامنة
# =========================
if AR:
    print("\nاكتب رقم عدد التحميلات المتزامنة")
    print("مثال: 8 ")
else:
    print("\nEnter simultaneous download count")
    print("Example: 8 ")

threads_input = input("Threads: ").strip()

if threads_input.isdigit():
    max_threads = int(threads_input)
else:
    max_threads = 8

# =========================
# تجهيز الروابط
# =========================
identifier = url_input.split("/details/")[-1].strip("/")

META = f"https://archive.org/metadata/{identifier}"
BASE = f"https://archive.org/download/{identifier}"

data = requests.get(META).json()

# =========================
# اسم المجلد
# =========================
folder = data.get("metadata", {}).get("title", identifier)
folder = re.sub(r'[\\/*?:"<>|]', "", folder).strip()

os.makedirs(folder, exist_ok=True)

# =========================
# استخراج الصيغ
# =========================
formats = set()

for f in data["files"]:
    name = f.get("name", "")

    if "." in name:
        ext = "." + name.split(".")[-1].lower()
        formats.add(ext)

formats = sorted(formats)

# =========================
# عرض الصيغ
# =========================
print(TXT["formats"])

for i, ext in enumerate(formats, 1):
    print(f"{i} - {ext}")

# =========================
# شرح الإدخال
# =========================
if AR:
    print("\nاكتب الأرقام مفصولة بفاصلة مثل: 1,3")
else:
    print("\nEnter numbers separated by commas like: 1,3")

choice = input("Select: ").strip()

# =========================
# الصيغ المختارة
# =========================
selected_formats = []

for x in choice.split(","):
    x = x.strip()

    if x.isdigit():
        idx = int(x) - 1

        if 0 <= idx < len(formats):
            selected_formats.append(formats[idx])

if not selected_formats:
    print(TXT["invalid"])
    exit()

print(TXT["selected"], ", ".join(selected_formats))

# =========================
# تجهيز الملفات
# =========================
files = []

for f in data["files"]:
    name = f.get("name", "")

    if not any(name.lower().endswith(ext) for ext in selected_formats):
        continue

    title = f.get("title") or os.path.splitext(name)[0]

    clean = re.sub(r'[\\/*?:"<>|]', "", title).strip()

    ext = "." + name.split(".")[-1]

    files.append((name, clean, ext))

# =========================
# التحميل
# =========================
def download(item):
    name, clean, ext = item

    file_url = f"{BASE}/{name}"
    path = f"{folder}/{clean}{ext}"

    if os.path.exists(path):
        print(TXT["skip"], clean)
        return

    print(TXT["downloading"], clean)

    r = requests.get(file_url, stream=True)

    with open(path, "wb") as f:
        for chunk in r.iter_content(1024 * 1024):
            if chunk:
                f.write(chunk)

# =========================
# بدء التحميل
# =========================
print(f"{TXT['folder']} {folder}")
print(f"{TXT['files']} {len(files)}")
print(f"Threads: {max_threads}\n")

with ThreadPoolExecutor(max_workers=max_threads) as exe:
    exe.map(download, files)

print(TXT["done"])
