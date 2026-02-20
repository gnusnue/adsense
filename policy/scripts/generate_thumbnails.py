#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
SIZE = (1200, 675)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[\s_]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "unknown"


def fit_cover(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    return ImageOps.fit(image, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def load_font(font_candidates: list[Path], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    bundled_candidates = [
        ROOT / "apps/site/assets/fonts/NotoSansCJKkr-Bold.otf",
        ROOT / "apps/site/assets/fonts/NotoSansCJKkr-Regular.otf",
        ROOT / "apps/site/assets/fonts/NotoSansKR-Bold.ttf",
        ROOT / "apps/site/assets/fonts/NotoSansKR-Regular.ttf",
    ]
    preferred = font_candidates + [p for p in bundled_candidates if p not in font_candidates]
    for candidate in preferred:
        if candidate.exists():
            try:
                return ImageFont.truetype(str(candidate), size=size)
            except Exception:
                continue
    for system_font in [
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        try:
            return ImageFont.truetype(system_font, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def wrap_title(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
    max_lines: int = 2,
) -> list[str]:
    compact = " ".join(text.split())
    if not compact:
        return [""]

    lines: list[str] = []
    current = ""
    idx = 0
    while idx < len(compact):
        ch = compact[idx]
        test = current + ch
        if draw.textlength(test, font=font) <= max_width:
            current = test
            idx += 1
            continue
        if current:
            lines.append(current)
            current = ""
        else:
            lines.append(ch)
            idx += 1
        if len(lines) >= max_lines:
            break

    if len(lines) < max_lines and current:
        lines.append(current)

    return lines[:max_lines]


def extract_highlight_text(text: str) -> str:
    compact = " ".join(text.split())
    if not compact:
        return ""
    amount_match = re.search(r"([0-9][0-9,\.]*(?:\s*)(?:만원|원|억원|천원|백만원|%))", compact)
    if amount_match:
        return amount_match.group(1).replace(" ", "")
    return ""


def compact_label(text: str, max_len: int = 16, max_items: int = 2) -> str:
    compact = " ".join(str(text or "").split())
    if not compact:
        return ""
    normalized = (
        compact.replace("，", ",")
        .replace("ㆍ", ",")
        .replace("·", ",")
        .replace("/", ",")
        .replace("|", ",")
    )
    parts = [part.strip() for part in normalized.split(",") if part.strip()]
    if not parts:
        return compact[:max_len].strip()
    deduped: list[str] = []
    seen: set[str] = set()
    for part in parts:
        if part in seen:
            continue
        seen.add(part)
        deduped.append(part)
    if len(deduped) <= max_items:
        label = ", ".join(deduped)
    else:
        label = ", ".join(deduped[:max_items]) + " 등"
    return label[:max_len].strip()


def compact_text_length(text: str) -> int:
    return len("".join(text.split()))


def size_by_char_count(
    text: str,
    max_size: int,
    min_size: int,
    short_count: int,
    long_count: int,
) -> int:
    if max_size <= min_size:
        return min_size
    if short_count >= long_count:
        return max_size

    count = compact_text_length(text)
    if count <= short_count:
        return max_size
    if count >= long_count:
        return min_size

    ratio = (count - short_count) / float(long_count - short_count)
    return int(round(max_size - (max_size - min_size) * ratio))


def text_size(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> tuple[int, int]:
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    return int(right - left), int(bottom - top)


def trim_text_to_width(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
) -> str:
    candidate = " ".join(str(text or "").split())
    if not candidate:
        return ""
    if " " in candidate:
        words = candidate.split(" ")
        while len(words) > 1 and draw.textlength(" ".join(words), font=font) > max_width:
            words = words[:-1]
        word_fit = " ".join(words).strip()
        if word_fit and draw.textlength(word_fit, font=font) <= max_width:
            return word_fit
    while candidate and draw.textlength(candidate, font=font) > max_width:
        candidate = candidate[:-1].rstrip()
    return candidate or "확인"


def fit_single_line_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_paths: list[Path],
    max_width: int,
    start_size: int,
    min_size: int,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    size = start_size
    while size >= min_size:
        font = load_font(font_paths, size)
        width, _ = text_size(draw, text, font)
        if width <= max_width:
            return font
        size -= 4
    return load_font(font_paths, min_size)


def fit_multiline_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_paths: list[Path],
    max_width: int,
    max_lines: int,
    start_size: int,
    min_size: int,
) -> tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, list[str]]:
    size = start_size
    while size >= min_size:
        font = load_font(font_paths, size)
        lines = wrap_title(draw, text, font, max_width=max_width, max_lines=max_lines)
        if all(text_size(draw, line, font)[0] <= max_width for line in lines):
            return font, lines
        size -= 4
    font = load_font(font_paths, min_size)
    return font, wrap_title(draw, text, font, max_width=max_width, max_lines=max_lines)


def draw_arrow_icon(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    outer_color: tuple[int, int, int, int] = (245, 245, 245, 255),
    inner_color: tuple[int, int, int, int] = (248, 23, 23, 255),
    arrow_color: tuple[int, int, int, int] = (255, 255, 255, 255),
) -> None:
    cx, cy = center
    outer_r = 108
    inner_r = 92

    draw.ellipse((cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r), fill=outer_color)
    draw.ellipse((cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r), fill=inner_color)

    arrow_points = [
        (cx - 48, cy - 15),
        (cx + 8, cy - 15),
        (cx + 8, cy - 48),
        (cx + 70, cy),
        (cx + 8, cy + 48),
        (cx + 8, cy + 15),
        (cx - 48, cy + 15),
    ]
    draw.polygon(arrow_points, fill=arrow_color)


def draw_pill(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill_color: tuple[int, int, int, int],
    text_color: tuple[int, int, int, int],
) -> int:
    text_w, text_h = text_size(draw, text, font)
    width = text_w + 46
    height = text_h + 24
    draw.rounded_rectangle((x, y, x + width, y + height), radius=20, fill=fill_color)
    draw.text((x + 23, y + 12), text, font=font, fill=text_color)
    return width


def render_thumbnail(
    base_image_path: Path,
    output_path: Path,
    title: str,
    region: str,
    target_group: str,
    category: str,
    benefit_text: str,
    font_paths: list[Path],
    size: tuple[int, int] = SIZE,
) -> None:
    with Image.open(base_image_path) as base_image:
        fitted = fit_cover(base_image.convert("RGB"), size)

    navy = (13, 49, 146)
    blue = (41, 101, 241)
    sky = (85, 186, 255)
    top_bg = (248, 246, 238)
    ink = (18, 24, 39)
    off_white = (246, 250, 255)
    badge_orange = (255, 116, 39)
    pill_bg = (224, 236, 255)
    canvas = Image.blend(fitted, Image.new("RGB", size, navy), 0.84).convert("RGBA")
    draw = ImageDraw.Draw(canvas, "RGBA")

    safe_region = compact_label(region, max_len=10, max_items=1) or "전국"
    safe_target = compact_label(target_group, max_len=18, max_items=2) or "일반"
    safe_category = compact_label(category, max_len=14, max_items=1) or "정책"

    top_split = int(size[1] * 0.48)
    draw.rectangle((6, 6, size[0] - 6, top_split), fill=(*top_bg, 255))
    draw.rectangle((0, top_split + 1, size[0], size[1]), fill=(*blue, 255))
    draw.rounded_rectangle((42, 26, 58, 178), radius=8, fill=(*sky, 255))

    headline_text = f"{safe_category} 지원"
    headline_font = fit_single_line_font(
        draw,
        headline_text,
        font_paths,
        max_width=size[0] - 130,
        start_size=size_by_char_count(headline_text, max_size=132, min_size=62, short_count=6, long_count=24),
        min_size=56,
    )
    headline_text = trim_text_to_width(draw, headline_text, headline_font, size[0] - 130)
    headline_w, headline_h = text_size(draw, headline_text, headline_font)
    draw.text(
        ((size[0] - headline_w) // 2, 24),
        headline_text,
        font=headline_font,
        fill=(*ink, 255),
        stroke_width=2,
        stroke_fill=(*ink, 255),
    )

    highlight_seed = extract_highlight_text(benefit_text) or extract_highlight_text(title)
    if highlight_seed:
        amount_text = f"{highlight_seed} 보장"
    else:
        amount_text = "지원 혜택 확인"

    amount_font = fit_single_line_font(
        draw,
        amount_text,
        font_paths,
        max_width=size[0] - 120,
        start_size=size_by_char_count(amount_text, max_size=90, min_size=44, short_count=6, long_count=26),
        min_size=40,
    )
    amount_text = trim_text_to_width(draw, amount_text, amount_font, size[0] - 120)
    amount_w, amount_h = text_size(draw, amount_text, amount_font)
    amount_y = 28 + headline_h + 34
    draw.text(((size[0] - amount_w) // 2, amount_y), amount_text, font=amount_font, fill=(*navy, 255))

    divider_w = int(size[0] * 0.48)
    divider_x1 = (size[0] - divider_w) // 2
    divider_y = amount_y + amount_h + 20
    draw.rounded_rectangle((divider_x1, divider_y, divider_x1 + divider_w, divider_y + 10), radius=7, fill=(*sky, 255))

    pill_seed = f"{safe_region}{safe_target}"
    pill_font = fit_single_line_font(
        draw,
        f"{safe_region} · {safe_target}",
        font_paths,
        max_width=460,
        start_size=size_by_char_count(pill_seed, max_size=38, min_size=28, short_count=5, long_count=20),
        min_size=28,
    )
    pill_region_text = trim_text_to_width(draw, safe_region, pill_font, 170)
    pill_target_text = trim_text_to_width(draw, safe_target, pill_font, 260)
    pill_y = divider_y + 20
    left_pill_w = draw_pill(
        draw,
        x=108,
        y=pill_y,
        text=pill_region_text or "전국",
        font=pill_font,
        fill_color=(*pill_bg, 255),
        text_color=(*navy, 255),
    )
    draw_pill(
        draw,
        x=108 + left_pill_w + 16,
        y=pill_y,
        text=pill_target_text or "일반",
        font=pill_font,
        fill_color=(*pill_bg, 255),
        text_color=(*navy, 255),
    )

    cta_primary = f"나도 {safe_target} 대상자?"
    cta_secondary = f"{safe_region} {safe_category} 지원받기".strip()

    cta_font = fit_single_line_font(
        draw,
        cta_primary,
        font_paths,
        max_width=660,
        start_size=size_by_char_count(cta_primary, max_size=104, min_size=36, short_count=8, long_count=42),
        min_size=32,
    )
    primary_line = trim_text_to_width(draw, cta_primary, cta_font, 660)

    secondary_font = fit_single_line_font(
        draw,
        cta_secondary,
        font_paths,
        max_width=660,
        start_size=size_by_char_count(cta_secondary, max_size=98, min_size=34, short_count=10, long_count=42),
        min_size=30,
    )
    secondary_line = trim_text_to_width(draw, cta_secondary, secondary_font, 660)

    left_x = 48
    first_y = top_split + 70
    draw.text((left_x, first_y), primary_line, font=cta_font, fill=(*off_white, 255))
    _, first_h = text_size(draw, primary_line, cta_font)
    second_y = first_y + first_h + 14
    draw.text((left_x, second_y), secondary_line, font=secondary_font, fill=(*off_white, 255))

    badge_text = "지금 확인"
    badge_font = fit_single_line_font(draw, badge_text, font_paths, max_width=250, start_size=42, min_size=30)
    badge_w, badge_h = text_size(draw, badge_text, badge_font)
    badge_x = size[0] - 380
    badge_y = top_split + 34
    draw.rounded_rectangle(
        (badge_x, badge_y, badge_x + badge_w + 48, badge_y + badge_h + 24),
        radius=18,
        fill=(*badge_orange, 255),
    )
    draw.text((badge_x + 24, badge_y + 12), badge_text, font=badge_font, fill=(255, 255, 255, 255))

    draw_arrow_icon(
        draw,
        center=(size[0] - 146, top_split + 178),
        outer_color=(244, 247, 252, 255),
        inner_color=(*badge_orange, 255),
        arrow_color=(255, 255, 255, 255),
    )

    for i in range(4):
        draw.rectangle((i, i, size[0] - 1 - i, size[1] - 1 - i), outline=(*navy, 255), width=1)

    ensure_dir(output_path.parent)
    canvas.convert("RGB").save(output_path, format="JPEG", quality=90, optimize=True)


def generate_thumbnails_for_policies(
    policies: list[dict[str, Any]],
    base_image_path: Path,
    output_dir: Path,
    site_base_url: str,
    font_paths: list[Path],
) -> dict[str, Any]:
    if not base_image_path.exists():
        raise RuntimeError(f"thumbnail base image not found: {base_image_path}")

    ensure_dir(output_dir)

    items: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    for rec in policies:
        policy_id = str(rec.get("policy_id", "")).strip()
        if not policy_id:
            continue
        slug = slugify(policy_id)
        output_path = output_dir / f"{slug}.jpg"
        try:
            render_thumbnail(
                base_image_path=base_image_path,
                output_path=output_path,
                title=str(rec.get("title", "")).strip(),
                region=str(rec.get("region", "")).strip(),
                target_group=str(rec.get("target_group", "")).strip(),
                category=str(rec.get("category", "")).strip(),
                benefit_text=str(rec.get("benefit_text", "")).strip(),
                font_paths=font_paths,
            )
            relative_path = f"/assets/thumbnails/{slug}.jpg"
            public_url = f"{site_base_url.rstrip('/')}{relative_path}"
            items.append(
                {
                    "policy_id": policy_id,
                    "slug": slug,
                    "relative_path": relative_path,
                    "public_url": public_url,
                    "official_url": str(rec.get("official_url", "")).strip(),
                }
            )
        except Exception as exc:  # noqa: BLE001
            errors.append({"policy_id": policy_id, "slug": slug, "error": str(exc)})

    return {"generated": len(items), "errors": errors, "items": items}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate policy thumbnails from canonical data")
    parser.add_argument("--canonical", required=True)
    parser.add_argument("--base-image", default="apps/site/assets/thumbnail/base.png")
    parser.add_argument("--output-dir", default="apps/site/dist/assets/thumbnails")
    parser.add_argument("--site-base-url", default="https://pol.cbbxs.com")
    parser.add_argument("--manifest-out", default="artifacts/latest/frontend/thumbnails.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    canonical_path = ROOT / args.canonical
    if not canonical_path.exists():
        print(f"[ERROR] canonical not found: {canonical_path}")
        return 1

    data = read_json(canonical_path)
    if not isinstance(data, list):
        print("[ERROR] canonical must be list")
        return 1
    active = [x for x in data if isinstance(x, dict) and x.get("status") == "active"]

    base_image_path = Path(args.base_image)
    if not base_image_path.is_absolute():
        base_image_path = ROOT / base_image_path

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir

    manifest_out = Path(args.manifest_out)
    if not manifest_out.is_absolute():
        manifest_out = ROOT / manifest_out

    result = generate_thumbnails_for_policies(
        policies=active,
        base_image_path=base_image_path,
        output_dir=output_dir,
        site_base_url=args.site_base_url,
        font_paths=[
            ROOT / "apps/site/assets/fonts/NotoSansCJKkr-Bold.otf",
            ROOT / "apps/site/assets/fonts/NotoSansCJKkr-Regular.otf",
            ROOT / "apps/site/assets/fonts/NotoSansKR-Bold.ttf",
            ROOT / "apps/site/assets/fonts/NotoSansKR-Regular.ttf",
        ],
    )
    write_json(manifest_out, result["items"])
    print(f"generated thumbnails: {result['generated']}")
    if result["errors"]:
        print(f"thumbnail errors: {len(result['errors'])}")
        for item in result["errors"][:5]:
            print(f"- {item['policy_id']}: {item['error']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
