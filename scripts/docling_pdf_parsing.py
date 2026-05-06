import requests
import fitz  # PyMuPDF
import os
import time
import re
from PIL import Image
import io

from docling.document_converter import DocumentConverter

# ==============================
# TIMER
# ==============================
start_time = time.perf_counter()

# ==============================
# CONFIG
# ==============================
PDF_URL = "https://vehicleinfo.mopar.com/assets/publications/en-us/Fiat/2020/124_Spider/P116418_20_BA_OM_EN_USC_DIGITAL.pdf"
PDF_PATH = "temp.pdf"
OUTPUT_MD = "output.md"
IMAGE_DIR = "images"

os.makedirs(IMAGE_DIR, exist_ok=True)

# ==============================
# DOWNLOAD PDF
# ==============================
print("Downloading PDF...")
response = requests.get(PDF_URL)
response.raise_for_status()

with open(PDF_PATH, "wb") as f:
    f.write(response.content)

print("✅ Download complete")

# ==============================
# OPEN PDF
# ==============================
doc = fitz.open(PDF_PATH)
total_pages = len(doc)
print(f"Total pages: {total_pages}")

# ==============================
# EXTRACT IMAGES PER PAGE
# ==============================
print("Extracting images...")

page_images = {}

for page_index in range(total_pages):
    page = doc[page_index]
    images = page.get_images(full=True)

    page_images[page_index] = []
    local_counter = 1

    for img in images:
        try:
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]

            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

            img_name = f"image_{page_index+1}_{local_counter}.jpg"
            img_path = os.path.join(IMAGE_DIR, img_name)

            image.save(img_path)

            page_images[page_index].append(img_name)
            local_counter += 1

        except Exception as e:
            print(f"⚠️ Skip image page {page_index+1}: {e}")

print("✅ Image extraction done")

# ==============================
# INIT DOCLING (NO OCR → FAST)
# ==============================
converter = DocumentConverter()

# ==============================
# OUTPUT FILE
# ==============================
with open(OUTPUT_MD, "w", encoding="utf-8") as f:
    f.write("# PDF Extraction Output\n\n")

# ==============================
# PROCESS PAGE BY PAGE
# ==============================
for page_index in range(total_pages):

    print(f"Processing page {page_index+1}...")

    try:
        result = converter.convert(
            PDF_PATH,
            page_range=(page_index + 1, page_index + 1),
        )

        md = result.document.export_to_markdown()

        imgs = page_images.get(page_index, [])
        img_counter = [0]

        # ==============================
        # REPLACE <!-- image --> WITH REAL IMAGE
        # ==============================
        def replace_image(match):
            if img_counter[0] < len(imgs):
                img_name = imgs[img_counter[0]]
                img_counter[0] += 1
                return f"\n![Image](images/{img_name})\n"
            return ""

        md = re.sub(r"<!-- image -->", replace_image, md)

        # ==============================
        # WRITE OUTPUT
        # ==============================
        with open(OUTPUT_MD, "a", encoding="utf-8") as f:
            f.write(f"\n\n## Page {page_index+1}\n\n")
            f.write(md)
            f.flush()

        print(f"✅ Page {page_index+1} done")

    except Exception as e:
        print(f"❌ Error page {page_index+1}: {e}")

# ==============================
# DONE
# ==============================
end_time = time.perf_counter()

print("\n==============================")
print(f"✅ Markdown saved to: {OUTPUT_MD}")
print(f"⏱️ Total time: {(end_time - start_time)/60:.2f} min")
print("==============================")