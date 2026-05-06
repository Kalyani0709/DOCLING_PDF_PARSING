import re
import json

INPUT_FILE = "output.md"
OUTPUT_FILE = "data/chunked.json"

PDF_URL = "https://vehicleinfo.mopar.com/assets/publications/en-us/Fiat/2020/124_Spider/P116418_20_BA_OM_EN_USC_DIGITAL.pdf"
YEAR = "2020"
MAKE = "Fiat"
MODEL = "124 Spider"


# ----------------------------
# CLEAN TEXT
# ----------------------------
def clean_text(text):
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ----------------------------
# REMOVE HEADER
# ----------------------------
def remove_header(content):
    if "# PDF Extraction Output" in content:
        content = content.split("# PDF Extraction Output", 1)[-1]
    return content.strip()


# ----------------------------
# SPLIT INTO PAGES
# ----------------------------
def split_pages(content):
    pattern = r"## Page (\d+)"
    splits = re.split(pattern, content)

    pages = []
    for i in range(1, len(splits), 2):
        pages.append({
            "page": int(splits[i]),
            "text": splits[i + 1].strip()
        })

    return pages


# ----------------------------
# TOC DETECTION
# ----------------------------
def is_toc(text):
    lines = text.split("\n")
    score = sum(1 for l in lines if "...." in l or "|" in l)
    return score > 5


# ----------------------------
# GENERIC TABLE DETECTOR (NO HARDCODING)
# ----------------------------
def is_structured_block(text):
    """
    Detects table-like or multi-entity structured content
    """
    lines = text.split("\n")

    pipe_lines = [l for l in lines if "|" in l]
    long_lines = [l for l in lines if len(l.split()) > 15]

    # Heuristics (generic)
    if len(pipe_lines) >= 3 and len(long_lines) >= 2:
        return True

    return False


# ----------------------------
# GENERIC ROW SPLITTER
# ----------------------------
def split_structured_rows(section_name, text):
    """
    Splits structured/table content into meaningful chunks
    """
    rows = re.split(r"\|\s*\|", text)

    chunks = []

    for row in rows:
        row = row.strip()

        # skip empty / noise
        if len(row.split()) < 10:
            continue

        # remove separators
        row = re.sub(r"-{3,}", "", row)

        chunks.append({
            "section": section_name,
            "text": row
        })

    return chunks


# ----------------------------
# CLEAN SECTION TITLE
# ----------------------------
def clean_section(section):
    section = re.sub(r"\s+", " ", section.strip())
    return section[:120]


# ----------------------------
# HEADING DETECTORS
# ----------------------------
def is_main_heading(line):
    if not line:
        return False
    if len(line.split()) > 10:
        return False
    if line.isupper():
        return True
    if len(line.split()) <= 4:
        return True
    return False


def is_subheading(line):
    line = line.lower()
    return line.startswith("if equipped") or (line.endswith(":") and len(line.split()) > 3)


def is_annotation(line):
    line = line.upper()
    return any(line.startswith(x) for x in ["NOTE", "WARNING", "CAUTION", "IMPORTANT"])


# ----------------------------
# EXTRACT SECTIONS
# ----------------------------
def extract_sections(page_text):
    lines = page_text.split("\n")

    sections = []
    section_stack = []
    buffer = ""

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("##"):
            heading = clean_section(line.replace("##", ""))

            if heading.lower() in ["page", "image"]:
                continue

            if is_annotation(heading) or is_subheading(heading):
                buffer += f"\n{heading}\n"
                continue

            if is_main_heading(heading):
                if section_stack and buffer.strip():
                    sections.append({
                        "section": " > ".join(section_stack),
                        "text": buffer.strip()
                    })

                if len(heading.split()) <= 3:
                    section_stack = [heading]
                else:
                    section_stack = section_stack[:1] + [heading] if section_stack else [heading]

                buffer = ""
                continue

        buffer += "\n" + line

    if section_stack and buffer.strip():
        sections.append({
            "section": " > ".join(section_stack),
            "text": buffer.strip()
        })

    return sections


# ----------------------------
# EXTRACT IMAGES
# ----------------------------
def extract_images(text):
    images = re.findall(r"!\[.*?\]\((.*?)\)", text)
    clean = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    return clean.strip(), images

def clean_table_noise(text):
    # remove markdown separators like -----
    text = re.sub(r"\|?\s*-{3,}\s*\|?", " ", text)

    return text.strip()

# ----------------------------
# MAIN RUN
# ----------------------------
def run():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    content = remove_header(content)
    pages = split_pages(content)

    final_chunks = []

    for page_data in pages:
        page_num = page_data["page"]
        page_text = page_data["text"]

        if is_toc(page_text):
            continue

        sections = extract_sections(page_text)

        for sec_idx, sec in enumerate(sections):
            section_name = sec["section"]

            text, images = extract_images(sec["text"])
            text = clean_text(text)
            text = clean_table_noise(text)

            if not text:
                continue

            # 🔥 NEW: structured splitting (generic)
            if is_structured_block(text):

                structured_chunks = split_structured_rows(section_name, text)

                for i, sc in enumerate(structured_chunks):
                    chunk_id = f"{YEAR}_{MAKE}_{MODEL}_p{page_num}_s{sec_idx}_r{i}"

                    final_chunks.append({
                        "chunk_id": chunk_id,
                        "text": sc["text"],
                        "metadata": {
                            "pdf_url": PDF_URL,
                            "year": YEAR,
                            "make": MAKE,
                            "model": MODEL,
                            "page": page_num,
                            "section": section_name,
                            "images": images,
                            "type": "structured_row_chunk"
                        }
                    })

            else:
                chunk_id = f"{YEAR}_{MAKE}_{MODEL}_p{page_num}_s{sec_idx}"

                final_chunks.append({
                    "chunk_id": chunk_id,
                    "text": f"{section_name}: {text}",
                    "metadata": {
                        "pdf_url": PDF_URL,
                        "year": YEAR,
                        "make": MAKE,
                        "model": MODEL,
                        "page": page_num,
                        "section": section_name,
                        "images": images,
                        "type": "section_chunk"
                    }
                })

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_chunks, f, indent=2)

    print(f"✅ Created {len(final_chunks)} clean chunks")


if __name__ == "__main__":
    run()