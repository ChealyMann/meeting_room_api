"""The request slip (ប័ណ្ណស្នើ) as a Word file, laid out like the NBC signed paper.

A4. On top the logo with the bank's name and the national motto; "លេខ" with dots; the title;
then two columns: labels and the opinion boxes on the left, the text on the right, every text
line on a dashed rule (dashed underline, carried to the right edge by an underlined tab). Under
it the lunar date and the city date, the office head's box, and the booker's signature. The
address sits in the page footer. Text uses the Khmer fonts of the bank's own template.
"""

import io
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_UNDERLINE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Mm, Pt, RGBColor

from app.services.request_slip_data import SlipData, SlipSigner

BODY_FONT = "Khmer OS Battambang"
LABEL_FONT = "Khmer OS Muol Light"
INK_BLUE = RGBColor(0x1F, 0x3A, 0x93)  # the opinion boxes, like a pen
LOGO = Path(__file__).resolve().parent.parent / "assets" / "nbc-logo.png"

LEFT_CM, MIDDLE_CM, RIGHT_CM = 6.6, 6.3, 6.0  # 18.9 cm of text width
TEXT_CM = MIDDLE_CM + RIGHT_CM


def _run(paragraph, text: str, *, font=BODY_FONT, size=11.0, color=None, underline=None):
    """Add text with the Khmer (complex script) font and size set, which Word needs."""
    run = paragraph.add_run(text)
    run.font.name = font
    run.font.size = Pt(size)
    r_pr = run._element.get_or_add_rPr()
    fonts = r_pr.find(qn("w:rFonts"))
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fonts.set(qn(attr), font)
    size_cs = OxmlElement("w:szCs")
    size_cs.set(qn("w:val"), str(int(size * 2)))
    r_pr.find(qn("w:sz")).addnext(size_cs)
    if color is not None:
        run.font.color.rgb = color
    if underline is not None:
        run.font.underline = underline
    return run


def _tight(paragraph, *, align=None, before=0.0, after=0.0, line=1.15):
    fmt = paragraph.paragraph_format
    fmt.space_before, fmt.space_after, fmt.line_spacing = Pt(before), Pt(after), line
    if align is not None:
        paragraph.alignment = align
    return paragraph


def _tiny(paragraph):
    """Word puts an empty paragraph after every table. Make it 1 pt tall, so it takes no room
    (and cannot fall alone onto a second page)."""
    fmt = paragraph.paragraph_format
    fmt.space_before = fmt.space_after = Pt(0)
    fmt.line_spacing = Pt(1)
    mark = OxmlElement("w:rPr")
    size = OxmlElement("w:sz")
    size.set(qn("w:val"), "2")
    mark.append(size)
    paragraph._p.get_or_add_pPr().append(mark)
    return paragraph


def _keep_whole(row) -> None:
    """A table row that never breaks across two pages (it moves to the next page whole)."""
    row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))


def _first(cell):
    """A new cell's empty first paragraph, made tight."""
    return _tight(cell.paragraphs[0])


def _plain_table(parent, rows: int, widths_cm: list[float]):
    """A table with no borders and fixed column widths."""
    table = parent.add_table(rows=rows, cols=len(widths_cm))
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    table._tbl.tblPr.append(layout)
    for row in table.rows:
        for cell, width in zip(row.cells, widths_cm, strict=True):
            cell.width = Cm(width)
    return table


def _label(cell_or_paragraph, text: str, *, align=WD_ALIGN_PARAGRAPH.LEFT, new=True):
    paragraph = cell_or_paragraph.add_paragraph() if new else cell_or_paragraph
    _tight(paragraph, align=align, line=1.3)
    _run(paragraph, text, font=LABEL_FONT, size=10.5, underline=True)
    return paragraph


def _ruled(cell, text: str, *, indent_cm=0.0, first_line_cm=0.0, new=True):
    """One paragraph of text on dashed rules that run to the cell's right edge."""
    paragraph = cell.add_paragraph() if new else cell.paragraphs[0]
    _tight(paragraph, align=WD_ALIGN_PARAGRAPH.LEFT, line=1.25)
    fmt = paragraph.paragraph_format
    fmt.left_indent = Cm(indent_cm)
    fmt.first_line_indent = Cm(first_line_cm)
    fmt.tab_stops.add_tab_stop(Cm(TEXT_CM - 0.35), WD_TAB_ALIGNMENT.RIGHT)
    _run(paragraph, text + "\t", underline=WD_UNDERLINE.DASH)
    return paragraph


def _signer(cell, signer: SlipSigner | None) -> None:
    """One signed opinion box: the comment, the signature, the date and the name."""
    if signer is None:
        return
    comment = _tight(cell.add_paragraph(), line=1.2)
    comment.paragraph_format.first_line_indent = Cm(0.6)
    _run(comment, signer.comment, size=10.5, color=INK_BLUE)
    if signer.signature is not None:
        picture = _tight(cell.add_paragraph(), align=WD_ALIGN_PARAGRAPH.CENTER)
        picture.add_run().add_picture(str(signer.signature), width=Cm(2.6))
    date_line = _tight(cell.add_paragraph(), align=WD_ALIGN_PARAGRAPH.CENTER)
    _run(date_line, signer.date, size=10.5, color=INK_BLUE)
    name = _tight(cell.add_paragraph(), align=WD_ALIGN_PARAGRAPH.CENTER, line=1.3)
    _run(name, f"{signer.title} {signer.name}".strip(), font=LABEL_FONT, size=10.5)


def _header(document) -> None:
    table = _plain_table(document, 1, [8.2, 10.7])
    brand, motto = table.rows[0].cells
    logo = _tight(_first(brand), align=WD_ALIGN_PARAGRAPH.CENTER)
    logo.add_run().add_picture(str(LOGO), width=Cm(2.4))
    name = _tight(brand.add_paragraph(), align=WD_ALIGN_PARAGRAPH.CENTER, line=1.2)
    _run(name, "ធនាគារជាតិ នៃ កម្ពុជា", font=LABEL_FONT, size=16)
    first = _tight(_first(motto), align=WD_ALIGN_PARAGRAPH.CENTER, before=8, line=1.4)
    _run(first, "ព្រះរាជាណាចក្រកម្ពុជា", font=LABEL_FONT, size=12)
    second = _tight(motto.add_paragraph(), align=WD_ALIGN_PARAGRAPH.CENTER, line=1.4)
    _run(second, "ជាតិ  សាសនា  ព្រះមហាក្សត្រ", font=LABEL_FONT, size=12)
    number = _tight(document.add_paragraph(), before=4)
    number.paragraph_format.left_indent = Cm(0.8)
    _run(number, "លេខ" + "." * 55, size=10.5)
    title = _tight(document.add_paragraph(), align=WD_ALIGN_PARAGRAPH.CENTER, before=2, after=4)
    title.paragraph_format.left_indent = Cm(4)
    _run(title, "ប័ណ្ណស្នើ", font=LABEL_FONT, size=14, underline=True)


def _timetable(cell, rows: list[tuple[str, str, str]]) -> None:
    table = cell.add_table(rows=len(rows) + 1, cols=3)
    table.style = "Table Grid"
    table.autofit = False
    for row, values in zip(table.rows, [("ល.រ", "កាលបរិច្ឆេទ", "វេលាម៉ោង"), *rows], strict=True):
        for box, width, value in zip(row.cells, (1.1, 6.0, 4.6), values, strict=True):
            box.width = Cm(width)
            _run(_first(box), value, size=9.5)
    _tiny(cell.paragraphs[-1])


def _body(document, data: SlipData) -> None:
    right = WD_ALIGN_PARAGRAPH.RIGHT
    director = f"{data.director_title}នាយកខុទ្ទកាល័យ"
    table = _plain_table(document, 5, [LEFT_CM, TEXT_CM])
    rows = [row.cells for row in table.rows]

    _label(_first(rows[0][0]), "គោរពជូន", align=right, new=False)
    _ruled(rows[0][1], f"៖ {director}", new=False)

    _label(_first(rows[1][0]), "តាមរយៈ", align=right, new=False)
    _ruled(rows[1][1], f"៖ - {data.department_line}", new=False)
    _first(rows[2][0])
    _ruled(rows[2][1], f"- {data.office_line}", indent_cm=0.35, new=False)

    _label(_first(rows[3][0]), "កម្មវត្ថុ", align=right, new=False)
    _label(rows[3][0], f"មតិ{director}")
    _signer(rows[3][0], data.director)
    text = rows[3][1]
    _ruled(text, f"៖ {data.subject}", new=False)
    if data.timetable:
        _timetable(text, data.timetable)
        _ruled(text, data.people_line, indent_cm=0.35)
    _ruled(text, "ស្នើសុំរៀបចំ៖", indent_cm=0.35)
    for line in data.requests:
        _ruled(text, line, indent_cm=0.35)
    if not data.timetable:
        _ruled(text, "", indent_cm=0.35)  # the paper's spare line; a timetable needs the room

    _keep_whole(table.rows[4])
    # The department head's box starts beside the closing lines and runs down the left, with
    # the dates, the office head's box and the booker on its right, as on the paper.
    _tight(_first(rows[4][0]), line=1.25)
    _label(rows[4][0], f"មតិ{data.department_head_title}ប្រធាននាយកដ្ឋាន")
    _signer(rows[4][0], data.department_head)
    _ruled(rows[4][1], data.closing[0], first_line_cm=1.1, new=False)
    _ruled(rows[4][1], data.closing[1])
    _bottom(rows[4][1], data)


def _bottom(cell, data: SlipData) -> None:
    for number, line in enumerate((data.lunar_line, data.city_date)):
        dates = _tight(cell.add_paragraph(), align=WD_ALIGN_PARAGRAPH.RIGHT, line=1.3)
        dates.paragraph_format.space_before = Pt(6 if number == 0 else 0)
        _run(dates, line)
    table = _plain_table(cell, 1, [MIDDLE_CM - 0.2, RIGHT_CM - 0.2])
    _tiny(cell.paragraphs[-1])
    _keep_whole(table.rows[0])
    office, maker = table.rows[0].cells
    _label(_first(office), f"មតិ{data.office_head_title}ប្រធានការិយាល័យ", new=False)
    _signer(office, data.office_head)
    centre = WD_ALIGN_PARAGRAPH.CENTER
    _run(_tight(_first(maker), align=centre), "អ្នកធ្វើប័ណ្ណ")
    signature = _tight(maker.add_paragraph(), align=centre)
    if data.maker.signature is not None:
        signature.add_run().add_picture(str(data.maker.signature), width=Cm(2.8))
    else:
        _tight(maker.add_paragraph())  # room to sign by hand
        _tight(maker.add_paragraph())
    _run(_tight(maker.add_paragraph(), align=centre, line=1.5), data.maker.name, font=LABEL_FONT)


def render_slip_docx(data: SlipData) -> bytes:
    document = Document()
    section = document.sections[0]
    section.page_width, section.page_height = Mm(210), Mm(297)
    section.top_margin, section.bottom_margin = Cm(1.2), Cm(1.4)
    section.left_margin, section.right_margin = Cm(1.0), Cm(1.1)
    section.footer_distance = Cm(0.6)

    _header(document)
    _body(document, data)
    _tiny(document.add_paragraph())

    footer = _tight(section.footer.paragraphs[0], align=WD_ALIGN_PARAGRAPH.CENTER)
    _run(footer, data.address, size=7.5)

    out = io.BytesIO()
    document.save(out)
    return out.getvalue()
