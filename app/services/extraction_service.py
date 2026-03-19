import os
import re
import logging
import pandas as pd
import camelot
import pdfplumber
from app.core.config import settings
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)


def get_env_str(name, default):
    value = os.getenv(name, default)
    if value is None:
        return default
    value = value.strip().strip('"').strip("'")
    return value


def get_env_bool(name, default):
    value = get_env_str(name, str(default)).lower()
    if value in ("true", "1", "yes"):
        return True
    elif value in ("false", "0", "no"):
        return False
    else:
        return default


def get_env_int(name, default):
    value = get_env_str(name, str(default))
    try:
        return int(value)
    except ValueError:
        logger.warning(f"Invalid integer for {name}: {value}, using default {default}")
        return default


DEBUG = get_env_bool("DEBUG", False)
USE_PDFPLUMBER_FALLBACK = get_env_bool("USE_PDFPLUMBER_FALLBACK", True)
PAGES = get_env_str("PAGES", "all")  # for Camelot


def clean_text(text: str) -> str:
    """
    Clean extracted text by replacing common Unicode issues and normalizing spaces.
    """
    # Replace problematic Unicode characters with ASCII equivalents
    replacements = {
        'ΓÇÖ': "'",
        'ΓÇ£': '"',
        'ΓÇ¥': '"',
        'ΓÇª': '...',
        'ΓÇö': '—',
        'ΓÇô': '-',
        'ΓÇÿ': "'",
        'ΓÇÖ': "'",
        'ΓÇ╛': '',
        'ΓÇó': '-',
        'ΓÇó': '-',
        'ΓÇó': '-',
    }
    for k, v in replacements.items():
        text = text.replace(k, v)

    # Remove control characters except newline and carriage return
    text = ''.join(ch for ch in text if ord(ch) >= 32 or ch in ('\n', '\r'))

    # Collapse multiple spaces into one
    text = re.sub(r' +', ' ', text)

    # Remove spaces at line beginnings
    text = re.sub(r'\n\s+', '\n', text)

    return text.strip()


def extract_tables_with_camelot(pdf_path: str) -> Tuple[List[pd.DataFrame], List[Dict]]:
    """
    Extract tables using Camelot. Returns (list of DataFrames, list of table metadata).
    Table metadata: {'page': int, 'bbox': [x1,y1,x2,y2]} in PDF units (bottom-left origin)
    """
    tables_df = []
    tables_meta = []
    for flavor in ["lattice", "stream"]:
        try:
            logger.info(f"Trying Camelot flavor: {flavor}")
            extracted = camelot.read_pdf(
                pdf_path,
                pages=PAGES,
                flavor=flavor,
                suppress_stdout=not DEBUG
            )
            if len(extracted) > 0:
                for table in extracted:
                    tables_df.append(table.df)
                    tables_meta.append({
                        'page': int(table.page),
                        'bbox': table._bbox  # [x1, y1, x2, y2] bottom-left origin
                    })
                logger.info(f"Camelot ({flavor}) found {len(tables_df)} tables")
                break
        except Exception as e:
            logger.warning(f"Camelot ({flavor}) failed: {e}")
    return tables_df, tables_meta


def extract_tables_with_pdfplumber(pdf_path: str) -> Tuple[List[pd.DataFrame], List[Dict]]:
    """
    Extract tables using pdfplumber. Returns (list of DataFrames, list of table metadata).
    Metadata uses pdfplumber bbox: (x0, top, x1, bottom) where top is from top of page.
    """
    tables_df = []
    tables_meta = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            table_settings = {
                "vertical_strategy": "text",
                "horizontal_strategy": "text",
                "intersection_tolerance": 5,
            }
            tables = page.find_tables(table_settings=table_settings)
            for table in tables:
                extracted_table = page.extract_table(table_settings)
                if extracted_table:
                    df = pd.DataFrame(extracted_table)
                    tables_df.append(df)
                    tables_meta.append({
                        'page': page_num,
                        'bbox': table.bbox  # (x0, top, x1, bottom)
                    })
            if DEBUG:
                logger.debug(f"Page {page_num}: found {len(tables)} tables via pdfplumber")
    return tables_df, tables_meta


def extract_text_with_placeholders(pdf_path: str, tables_meta: List[Dict]) -> str:
    """
    Extract full text from PDF, replacing each table region with a placeholder [Table N].
    The output is formatted as Markdown: paragraphs separated by blank lines,
    with placeholders on their own lines.
    """
    with pdfplumber.open(pdf_path) as pdf:
        # Sort tables by page and top coordinate (y0)
        tables_meta.sort(key=lambda t: (t['page'], t['bbox'][1]))

        all_text = []
        table_index = 1

        for page_num, page in enumerate(pdf.pages, start=1):
            # Get all words on page
            words = page.extract_words(keep_blank_chars=False, use_text_flow=True, extra_attrs=['fontname'])
            if not words:
                continue

            # Group words by line (approximate y0)
            lines = {}
            for w in words:
                y0 = round(w['top'], 1)
                if y0 not in lines:
                    lines[y0] = []
                lines[y0].append(w)

            # Sort lines by y0 (top to bottom)
            sorted_y = sorted(lines.keys())

            # Determine which tables are on this page
            page_tables = [t for t in tables_meta if t['page'] == page_num]

            # Build a list of objects (line text or placeholder) with their y0
            objects = []

            # Add lines, skipping those inside tables
            for y in sorted_y:
                line_words = lines[y]
                inside = False
                for t in page_tables:
                    x0, top, x1, bottom = t['bbox']
                    if top <= y <= bottom:
                        inside = True
                        break
                if not inside:
                    sorted_words = sorted(line_words, key=lambda w: w['x0'])
                    line_text = ' '.join([w['text'] for w in sorted_words])
                    objects.append(('line', y, line_text))

            # Add placeholders for tables on this page
            for t in page_tables:
                objects.append(('table', t['bbox'][1], f"[Table {table_index}]"))
                table_index += 1

            # Sort objects by y0 (top to bottom)
            objects.sort(key=lambda x: x[1])

            # Build page text (Markdown)
            page_lines = []
            for obj in objects:
                if obj[0] == 'line':
                    page_lines.append(obj[2])
                else:
                    # Placeholder on its own line, surrounded by blank lines for Markdown separation
                    page_lines.append('')
                    page_lines.append(obj[2])
                    page_lines.append('')
            if page_lines:
                page_text = '\n'.join(page_lines).strip()
                all_text.append(page_text)

        raw_text = '\n\n'.join(all_text)
        return clean_text(raw_text)


def extract_tables_from_pdf(pdf_path: str, output_dir: str) -> Tuple[str, str]:
    """
    Extract tables from PDF using Camelot (primary) and pdfplumber (fallback).
    Also extract full text with table placeholders (Markdown format).
    Returns (excel_path, full_text_markdown)
    """
    logger.info(f"Extracting tables from: {pdf_path}")

    # Step 1: Try Camelot
    tables_df, tables_meta = extract_tables_with_camelot(pdf_path)

    # Step 2: If no tables and fallback enabled, try pdfplumber
    if not tables_df and USE_PDFPLUMBER_FALLBACK:
        logger.info("Camelot found no tables; trying pdfplumber fallback")
        tables_df, tables_meta = extract_tables_with_pdfplumber(pdf_path)

    # Step 3: Extract full text with placeholders (Markdown)
    full_text_md = extract_text_with_placeholders(pdf_path, tables_meta)

    if not tables_df:
        logger.warning("No tables extracted; creating empty Excel")
        tables_df = [pd.DataFrame({"Info": ["No tables found in PDF"]})]

    # Save to Excel
    excel_path = os.path.join(output_dir, "extracted_tables.xlsx")
    try:
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            for i, df in enumerate(tables_df):
                sheet_name = f"Table_{i+1}" if i < len(tables_df)-1 else "Info"
                df.to_excel(writer, sheet_name=sheet_name, index=False, header=False)
        logger.info(f"Saved extracted tables to {excel_path}")
    except Exception as e:
        logger.error(f"Failed to save Excel file: {e}")
        raise

    return excel_path, full_text_md