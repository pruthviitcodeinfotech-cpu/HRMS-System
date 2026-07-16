"""Employee Management — Excel (.xlsx) export builder.

Builds a minimal, valid Office Open XML spreadsheet using only the standard
library. An ``.xlsx`` file is a ZIP package of XML parts; this module emits the
four mandatory parts (content types, package rels, workbook, worksheet) with all
cell values as inline strings. The project pins its dependency graph exactly
(``pyproject.toml`` + ``uv.lock``), so a stdlib writer is preferred over adding
``openpyxl`` for a single one-way export.

Scope: string-valued cells on a single sheet — exactly what the employee list
export needs. Not a general spreadsheet library.
"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Iterable
from xml.sax.saxutils import escape

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""

_PACKAGE_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

_WORKBOOK_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""


def _workbook_xml(sheet_name: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="{escape(sheet_name)}" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )


def _row_xml(values: Iterable[str]) -> str:
    cells = "".join(
        f"<c t=\"inlineStr\"><is><t xml:space=\"preserve\">{escape(value)}</t></is></c>"
        for value in values
    )
    return f"<row>{cells}</row>"


def _sheet_xml(headers: list[str], rows: Iterable[list[str]]) -> str:
    body = _row_xml(headers) + "".join(_row_xml(row) for row in rows)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{body}</sheetData>"
        "</worksheet>"
    )


def build_xlsx(
    headers: list[str], rows: Iterable[list[str]], *, sheet_name: str = "Employees"
) -> bytes:
    """Return the bytes of a single-sheet ``.xlsx`` with a header row plus data rows.

    All values are written as inline strings (the export is a human-readable
    snapshot, not a typed data interchange).
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES)
        archive.writestr("_rels/.rels", _PACKAGE_RELS)
        archive.writestr("xl/workbook.xml", _workbook_xml(sheet_name))
        archive.writestr("xl/_rels/workbook.xml.rels", _WORKBOOK_RELS)
        archive.writestr("xl/worksheets/sheet1.xml", _sheet_xml(headers, rows))
    return buffer.getvalue()
