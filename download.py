import os
import re
import requests
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

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
# استخراج المعرف
# =========================
def extract_identifier(url):
    path = urlparse(url).path.strip("/")

    if "details/" in path:
        return path.split("details/")[-1]

    if "download/" in path:
        parts = path.split("/")
        return parts[1] if len(parts) > 1 else parts[0]

    return path

identifier = extract_identifier(url_input)

# =========================
# API
# =========================
META = f"https://archive.org/metadata/{identifier}"
BASE = f"https://archive.org/download/{identifier}"

r = requests.get(META)

if r.status_code != 200:
    print("❌ لا يمكن جلب البيانات من archive.org")
    exit()

data = r.json()

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

for f in data.get("files", []):
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
# اختيار الصيغ
# =========================
if AR:
    print("\nاكتب الأرقام مفصولة بفاصلة مثل: 1,3")
else:
    print("\nEnter numbers separated by commas like: 1,3")

choice = input("Select: ").strip()

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

for f in data.get("files", []):
    name = f.get("name", "")

    if not any(name.lower().endswith(ext) for ext in selected_formats):
        continue

    title = f.get("title") or os.path.splitext(name)[0]
    clean = re.sub(r'[\\/*?:"<>|]', "", title).strip()

    ext = "." + name.split(".")[-1]

    files.append((name, clean, ext))

# =========================
# التحميل مع Progress Bar بدون مكتبات
# =========================
def download(item):
    name, clean, ext = item

    file_url = f"{BASE}/{name}"
    path = f"{folder}/{clean}{ext}"

    if os.path.exists(path):
        print(TXT["skip"], clean)
        return

    try:
        r = requests.get(file_url, stream=True, timeout=30)
        r.raise_for_status()

        total = int(r.headers.get("content-length", 0))
        downloaded = 0

        print(f"\n{TXT['downloading']} {clean}")

        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 512):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    # ===== Progress Bar =====
                    if total > 0:
                        percent = downloaded * 100 // total
                        bar_len = 20
                        filled = percent // 5
                        bar = "█" * filled + "-" * (bar_len - filled)

                        print(
                            f"\r[{bar}] {percent}% "
                            f"({downloaded//1024}KB/{total//1024}KB)",
                            end=""
                        )

        print(f"\n✔ تم التحميل: {clean}")

    except Exception as e:
        print(f"\n❌ خطأ في {clean}: {e}")

# =========================
# بدء التحميل
# =========================
max_threads = 8

print(f"{TXT['folder']} {folder}")
print(f"{TXT['files']} {len(files)}")
print(f"Threads: {max_threads}\n")

with ThreadPoolExecutor(max_workers=max_threads) as exe:
    exe.map(download, files)

print(TXT["done"])
