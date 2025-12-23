import asyncio
import os
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional

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


def _group_words_into_lines(words_list: List[Dict], y_tolerance: int = 5) -> List[Dict]:
    if not words_list:
        return []

    words_sorted = sorted(words_list, key=lambda w: (round(w["top"], 1), w["x0"]))
    lines: List[Dict] = []
    current_line = [words_sorted[0]]
    current_y = words_sorted[0]["top"]

    for word in words_sorted[1:]:
        if abs(word["top"] - current_y) <= y_tolerance:
            current_line.append(word)
        else:
            line_words = sorted(current_line, key=lambda w: w["x0"])
            lines.append(
                {
                    "text": " ".join(w["text"] for w in line_words),
                    "top": min(w["top"] for w in line_words),
                }
            )
            current_line = [word]
            current_y = word["top"]

    if current_line:
        line_words = sorted(current_line, key=lambda w: w["x0"])
        lines.append(
            {
                "text": " ".join(w["text"] for w in line_words),
                "top": min(w["top"] for w in line_words),
            }
        )

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
        x_left = None
        x_center = None
        y_center = None

        if rect:
            try:
                x0, y0, x1, y1 = rect
                x_left = x0
                x_center = (x0 + x1) / 2
                top = page.height - y1
                bottom = page.height - y0
                y_center = (top + bottom) / 2
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
                "x_left": x_left,
                "x_center": x_center,
                "y_center": y_center,
            }
        )

    return links


def _cluster_positions(positions: List[float], merge_threshold: float) -> List[Dict[str, float]]:
    if not positions:
        return []

    positions_sorted = sorted(positions)
    clusters = [[positions_sorted[0]]]
    for x in positions_sorted[1:]:
        if x - clusters[-1][-1] <= merge_threshold:
            clusters[-1].append(x)
        else:
            clusters.append([x])

    return [
        {"center": sum(cluster) / len(cluster), "size": float(len(cluster))}
        for cluster in clusters
    ]


def _column_boundaries_from_links(page_links: List[Dict], page_width: float) -> List[float]:
    positions = [link["x_left"] for link in page_links if link.get("x_left") is not None]
    if len(positions) < 2:
        return []

    merge_threshold = max(60.0, page_width * 0.06)
    clusters = _cluster_positions(positions, merge_threshold)
    if len(clusters) < 2:
        return []

    clusters = sorted(clusters, key=lambda c: c["size"], reverse=True)
    if len(clusters) > 3:
        clusters = clusters[:3]

    centers = sorted(c["center"] for c in clusters)
    if len(centers) < 2:
        return []

    return [(centers[i] + centers[i + 1]) / 2 for i in range(len(centers) - 1)]


def _detect_column_boundaries(
    words: List[Dict],
    page_width: float,
    page_links: List[Dict],
) -> List[float]:
    boundaries = _column_boundaries_from_links(page_links, page_width)
    if boundaries:
        return boundaries

    if not words:
        return []

    mid_x = page_width / 2
    left_count = 0
    right_count = 0
    for word in words:
        center_x = (word["x0"] + word["x1"]) / 2
        if center_x < mid_x:
            left_count += 1
        else:
            right_count += 1

    min_words = 10
    if left_count >= min_words and right_count >= min_words:
        return [mid_x]

    return []


def _split_words_into_columns(words: List[Dict], boundaries: List[float]) -> List[List[Dict]]:
    columns = [[] for _ in range(len(boundaries) + 1)]
    for word in words:
        center_x = word["x0"]
        col_index = 0
        while col_index < len(boundaries) and center_x >= boundaries[col_index]:
            col_index += 1
        columns[col_index].append(word)
    return columns


def _split_links_into_columns(page_links: List[Dict], boundaries: List[float]) -> List[List[Dict]]:
    columns = [[] for _ in range(len(boundaries) + 1)]
    for link in page_links:
        x_left = link.get("x_left")
        if x_left is None:
            columns[0].append(link)
            continue
        col_index = 0
        while col_index < len(boundaries) and x_left >= boundaries[col_index]:
            col_index += 1
        columns[col_index].append(link)

    for column_links in columns:
        column_links.sort(key=lambda link: link.get("y_center") or 0)

    return columns


def _inject_link(
    line: str,
    line_top: float,
    column_links: List[Dict],
    y_tolerance: int = 20,
) -> str:
    if "ВІДЕО" not in line:
        return line

    if not column_links:
        return line

    candidate_index: Optional[int] = None
    min_delta: Optional[float] = None
    for idx, link in enumerate(column_links):
        y_center = link.get("y_center")
        if y_center is None:
            continue
        delta = abs(y_center - line_top)
        if delta <= y_tolerance and (min_delta is None or delta < min_delta):
            candidate_index = idx
            min_delta = delta

    if candidate_index is None:
        for idx, link in enumerate(column_links):
            if link.get("context") and link["context"] in line:
                candidate_index = idx
                break

    if candidate_index is None:
        for idx, link in enumerate(column_links):
            if "ВІДЕО" in link.get("text", ""):
                candidate_index = idx
                break

    if candidate_index is None:
        return line

    link = column_links.pop(candidate_index)
    line = line.replace("ВІДЕО", f"ВІДЕО [{link['url']}]", 1)

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

            boundaries = _detect_column_boundaries(words, page.width, page_links)
            columns_words = _split_words_into_columns(words, boundaries)
            columns_links = _split_links_into_columns(page_links, boundaries)

            columns_lines = [
                _group_words_into_lines(column_words) for column_words in columns_words
            ]

            chunks.append(f"\n{'=' * 80}")
            chunks.append(f"СТОРІНКА {page_num}")
            chunks.append(f"{'=' * 80}\n")

            wrote_any_column = False
            for column_index, column_lines in enumerate(columns_lines):
                if not column_lines:
                    continue
                if wrote_any_column:
                    chunks.append("")
                wrote_any_column = True
                column_link_pool = columns_links[column_index]
                for line in column_lines:
                    processed = _inject_link(
                        line["text"],
                        line["top"],
                        column_link_pool,
                    )
                    chunks.append(processed)

            remaining_links = [link for column in columns_links for link in column]
            if remaining_links:
                chunks.append("\n--- Додаткові посилання ---")
                for idx, link in enumerate(remaining_links, start=1):
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
