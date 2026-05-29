import os
import re
import threading
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

    "error":
        "❌ خطأ:"
        if AR else
        "❌ Error:",

    "fetch_error":
        "❌ لا يمكن جلب البيانات من archive.org"
        if AR else
        "❌ Failed to fetch archive.org metadata",

    "choose":
        "\nاكتب الأرقام مفصولة بفاصلة مثل: 1,3"
        if AR else
        "\nEnter numbers separated by commas like: 1,3",
}

# =========================
# قفل الطباعة
# =========================
print_lock = threading.Lock()

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

try:

    r = requests.get(META, timeout=30)

    r.raise_for_status()

    data = r.json()

except Exception as e:

    print(TXT["fetch_error"])

    print(e)

    exit()

# =========================
# اسم المجلد
# =========================
folder = data.get("metadata", {}).get(
    "title",
    identifier
)

folder = re.sub(
    r'[\\/*?:"<>|]',
    "",
    folder
).strip()

if not folder:
    folder = identifier

os.makedirs(folder, exist_ok=True)

# =========================
# استخراج الصيغ
# =========================
formats = set()

for f in data.get("files", []):

    name = f.get("name", "").lower()

    if "." not in name:
        continue

    parts = name.split(".")

    # يسمح فقط بالملفات العادية
    # video.mp4 ✅
    # video.ia.mp4 ❌
    if len(parts) != 2:
        continue

    ext = "." + parts[-1]

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
print(TXT["choose"])

choice = input("Select: ").strip()

selected_formats = []

for x in choice.split(","):

    x = x.strip()

    if x.isdigit():

        idx = int(x) - 1

        if 0 <= idx < len(formats):

            selected_formats.append(
                formats[idx]
            )

selected_formats = list(
    set(selected_formats)
)

if not selected_formats:

    print(TXT["invalid"])

    exit()

print(
    TXT["selected"],
    ", ".join(selected_formats)
)

# =========================
# تجهيز الملفات
# =========================
files = []

for f in data.get("files", []):

    name = f.get("name", "")

    if not name:
        continue

    lower_name = name.lower()

    if "." not in lower_name:
        continue

    parts = lower_name.split(".")

    # =========================
    # منع الملفات المركبة
    # =========================
    if len(parts) != 2:
        continue

    ext = "." + parts[-1]

    # فقط الصيغ المختارة
    if ext not in selected_formats:
        continue

    title = (
        f.get("title")
        or os.path.splitext(
            os.path.basename(name)
        )[0]
    )

    clean = re.sub(
        r'[\\/*?:"<>|]',
        "",
        title
    ).strip()

    if not clean:

        clean = os.path.splitext(
            os.path.basename(name)
        )[0]

    files.append(
        (name, clean, ext)
    )

# =========================
# حذف التكرارات
# =========================
unique = {}

for item in files:
    unique[item[0]] = item

files = list(unique.values())

# =========================
# التحميل
# =========================
def download(item):

    name, clean, ext = item

    file_url = f"{BASE}/{name}"

    path = os.path.join(
        folder,
        clean + ext
    )

    # =========================
    # منع تكرار الأسماء
    # =========================
    counter = 1

    while os.path.exists(path):

        filename = (
            f"{clean}_{counter}{ext}"
        )

        path = os.path.join(
            folder,
            filename
        )

        counter += 1

    try:

        r = requests.get(
            file_url,
            stream=True,
            timeout=30
        )

        r.raise_for_status()

        total = int(
            r.headers.get(
                "content-length",
                0
            )
        )

        downloaded = 0

        last_percent = -1

        with print_lock:

            print(
                f"\n{TXT['downloading']} "
                f"{os.path.basename(path)}"
            )

        with open(path, "wb") as f:

            for chunk in r.iter_content(
                chunk_size=1024 * 512
            ):

                if not chunk:
                    continue

                f.write(chunk)

                downloaded += len(chunk)

                # =========================
                # Progress
                # =========================
                if total > 0:

                    percent = int(
                        downloaded * 100 / total
                    )

                    # تحديث كل 5%
                    if percent >= last_percent + 5:

                        last_percent = percent

                        bar_len = 20

                        filled = int(
                            bar_len * percent / 100
                        )

                        bar = (
                            "█" * filled +
                            "-" * (
                                bar_len - filled
                            )
                        )

                        with print_lock:

                            print(
                                f"[{bar}] "
                                f"{percent}% "
                                f"- "
                                f"{os.path.basename(path)}"
                            )

        with print_lock:

            print(
                f"✔ اكتمل: "
                f"{os.path.basename(path)}"
            )

    except Exception as e:

        with print_lock:

            print(
                f"\n{TXT['error']} "
                f"{clean}"
            )

            print(e)

# =========================
# بدء التحميل
# =========================
max_threads = 8

print(
    f"{TXT['folder']} "
    f"{folder}"
)

print(
    f"{TXT['files']} "
    f"{len(files)}"
)

print(f"Threads: {max_threads}\n")

with ThreadPoolExecutor(
    max_workers=max_threads
) as exe:

    exe.map(download, files)

print(TXT["done"])
