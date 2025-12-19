import asyncio
import os
from io import BytesIO
from pathlib import Path
from typing import Dict, List

import pdfplumber
from openai import AsyncOpenAI


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def _resolve_prompt_path() -> Path:
    """Return the path to training_preview_prompt.txt, trying a few likely locations."""
    this_file = Path(__file__).resolve()
    candidates = [
        this_file.parents[2] / "web_app" / "training_preview_prompt.txt",  # repo_root/web_app
        this_file.parents[1] / "web_app" / "training_preview_prompt.txt",  # app/web_app (fallback)
        Path.cwd() / "web_app" / "training_preview_prompt.txt",            # current working dir/web_app
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(f"Prompt not found. Tried: {', '.join(str(p) for p in candidates)}")


def _group_words_into_lines(words_list: List[Dict], y_tolerance: int = 5) -> List[str]:
    if not words_list:
        return []

    lines: List[str] = []
    current_line = [words_list[0]]
    current_y = words_list[0]["top"]

    for word in words_list[1:]:
        if abs(word["top"] - current_y) <= y_tolerance:
            current_line.append(word)
        else:
            lines.append(" ".join(w["text"] for w in current_line))
            current_line = [word]
            current_y = word["top"]

    if current_line:
        lines.append(" ".join(w["text"] for w in current_line))

    return lines


def _collect_links(page, page_num: int) -> List[Dict]:
    links: List[Dict] = []
    if not page.annots:
        return links

    for annot in page.annots:
        uri = None
        annot_data = annot.get("data", {})

        if "uri" in annot_data:
            uri = annot_data["uri"]
        elif "A" in annot_data and isinstance(annot_data["A"], dict):
            uri = annot_data["A"].get("URI")

        if uri and isinstance(uri, bytes):
            uri = uri.decode("utf-8")

        if not uri:
            continue

        rect = annot.get("rect")
        if not rect:
            x0 = annot.get("x0")
            y0 = annot.get("y0")
            x1 = annot.get("x1")
            y1 = annot.get("y1")
            if x0 is not None:
                rect = (x0, y0, x1, y1)

        link_text = "ВІДЕО"
        context_before = ""

        if rect:
            try:
                x0, y0, x1, y1 = rect
                cropped = page.within_bbox((x0, y0, x1, y1))
                extracted = cropped.extract_text()
                if extracted and extracted.strip():
                    link_text = extracted.strip()

                context_bbox = (max(0, x0 - 150), y0, x0, y1)
                context_crop = page.within_bbox(context_bbox)
                context_text = context_crop.extract_text()
                if context_text and context_text.strip():
                    words_before = context_text.strip().split()
                    context_before = " ".join(words_before[-3:]) if len(words_before) >= 3 else " ".join(words_before)
            except Exception:
                pass

        links.append(
            {
                "page": page_num,
                "text": link_text,
                "context": context_before,
                "url": str(uri),
                "rect": rect,
            }
        )

    return links


def _inject_link(line: str, page_links: List[Dict], mid_x: float, is_left: bool) -> str:
    if "ВІДЕО" not in line:
        return line

    for link in list(page_links):
        rect = link.get("rect")
        if rect is None:
            continue

        in_column = rect[0] < mid_x if is_left else rect[0] >= mid_x
        if not in_column:
            continue

        if link["context"] and link["context"] in line:
            line = line.replace("ВІДЕО", f"ВІДЕО [{link['url']}]", 1)
            page_links.remove(link)
            break
        if not link["context"] and "ВІДЕО" in link.get("text", ""):
            line = line.replace("ВІДЕО", f"ВІДЕО [{link['url']}]", 1)
            page_links.remove(link)
            break

    return line


def extract_training_text(pdf_bytes: bytes) -> str:
    if not pdf_bytes:
        raise ValueError("PDF is empty or unreadable")

    chunks: List[str] = []

    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            page_links = _collect_links(page, page_num)
            words = page.extract_words(x_tolerance=3, y_tolerance=3)

            if not words:
                continue

            mid_x = page.width / 2
            left_words = [w for w in words if w["x0"] < mid_x]
            right_words = [w for w in words if w["x0"] >= mid_x]

            left_words.sort(key=lambda w: (round(w["top"], 1), w["x0"]))
            right_words.sort(key=lambda w: (round(w["top"], 1), w["x0"]))

            left_lines = _group_words_into_lines(left_words)
            right_lines = _group_words_into_lines(right_words)

            chunks.append(f"\n{'=' * 80}")
            chunks.append(f"СТОРІНКА {page_num}")
            chunks.append(f"{'=' * 80}\n")

            for line in left_lines:
                processed = _inject_link(line, page_links, mid_x, is_left=True)
                chunks.append(processed)

            if right_lines:
                chunks.append("")
                for line in right_lines:
                    processed = _inject_link(line, page_links, mid_x, is_left=False)
                    chunks.append(processed)

            if page_links:
                chunks.append("\n--- Додаткові посилання ---")
                for idx, link in enumerate(page_links, start=1):
                    chunks.append(f"[{idx}] {link['url']}")

    return "\n".join(chunks).strip()


async def generate_training_preview_from_pdf(pdf_bytes: bytes, *, model: str = "gpt-4o") -> str:
    extracted_text = await asyncio.to_thread(extract_training_text, pdf_bytes)
    if not extracted_text:
        raise ValueError("Не вдалося витягнути текст із PDF")

    prompt_path = _resolve_prompt_path()
    system_prompt = prompt_path.read_text(encoding="utf-8")

    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")

    async with AsyncOpenAI(api_key=OPENAI_API_KEY) as client:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": extracted_text},
            ],
            temperature=0.2,
        )

    preview = response.choices[0].message.content if response.choices else ""
    if not preview:
        raise RuntimeError("OpenAI повернув порожнє превʼю")

    return preview.strip()
