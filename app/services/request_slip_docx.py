"""The request slip (ប័ណ្ណស្នើ) as a Word file, laid out like the NBC signed paper.

A4. On top the logo with the bank's name and the national motto; "លេខ" with dots; the title;
then two columns: labels and the opinion boxes on the left, the text on the right, every text
line on a dashed rule (dashed underline, carried to the right edge by an underlined tab). Under
it the lunar date and the city date, the office head's box, and the booker's signature. The
address sits in the page footer. Text uses the Khmer fonts of the bank's own template.

Always one page (owner, 13 Nov 2026): a long booking prints its timetable two sessions to a row,
and `fit_scale` shrinks every font, space and picture together when the content would not fit.
"""

import io
import math
import unicodedata
from contextvars import ContextVar
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
# The opinion boxes look written by hand, like the signed paper (owner, 13 Nov 2026).
PEN_FONT = "Khmer OS Freehand"
PEN_SIZE = 7.5  # the opinion comments and their dates (owner, 13 Nov 2026: "smaller")
INK_BLUE = RGBColor(0x1F, 0x3A, 0x93)  # the opinion boxes, like a pen
LOGO = Path(__file__).resolve().parent.parent / "assets" / "nbc-logo.png"

LEFT_CM, MIDDLE_CM, RIGHT_CM = 6.6, 6.3, 6.0  # 18.9 cm of text width
TEXT_CM = MIDDLE_CM + RIGHT_CM
TWO_PER_ROW_FROM = 5  # sessions: from this many the timetable prints two to a row

# How much every font, space and picture is scaled for this slip (1.0 = as designed).
_scale: ContextVar[float] = ContextVar("slip_scale", default=1.0)


def _pt(points: float) -> Pt:
    return Pt(points * _scale.get())


def _picture_cm(cm: float) -> Cm:
    return Cm(cm * _scale.get())


def _run(paragraph, text: str, *, font=BODY_FONT, size=11.0, color=None, underline=None):
    """Add text with the Khmer (complex script) font and size set, which Word needs."""
    run = paragraph.add_run(text)
    run.font.name = font
    run.font.size = _pt(size)
    r_pr = run._element.get_or_add_rPr()
    fonts = r_pr.find(qn("w:rFonts"))
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fonts.set(qn(attr), font)
    size_cs = OxmlElement("w:szCs")
    size_cs.set(qn("w:val"), str(max(2, round(size * _scale.get() * 2))))
    r_pr.find(qn("w:sz")).addnext(size_cs)
    if color is not None:
        run.font.color.rgb = color
    if underline is not None:
        run.font.underline = underline
    return run


def _tight(paragraph, *, align=None, before=0.0, after=0.0, line=1.15):
    fmt = paragraph.paragraph_format
    fmt.space_before, fmt.space_after, fmt.line_spacing = _pt(before), _pt(after), line
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


def _cell_padding(table, cm: float) -> None:
    """Thin left and right padding inside every cell (Word's default is 0.19 cm)."""
    margins = OxmlElement("w:tblCellMar")
    for side in ("left", "right"):
        edge = OxmlElement(f"w:{side}")
        edge.set(qn("w:w"), str(round(cm * 567)))  # twips
        edge.set(qn("w:type"), "dxa")
        margins.append(edge)
    table._tbl.tblPr.append(margins)


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


def _label(cell_or_paragraph, text: str, *, align=WD_ALIGN_PARAGRAPH.LEFT, new=True, box_cm=None):
    """A heading in the label font. With `box_cm`, smaller when it would not fit on one line
    (a long title such as លោកជំទាវ would push the slip onto a second page)."""
    paragraph = cell_or_paragraph.add_paragraph() if new else cell_or_paragraph
    _tight(paragraph, align=align, line=1.3)
    size = 10.5 if box_cm is None else _fit_size([text], 10.5, box_cm, LABEL_CM_PER_LETTER)
    _run(paragraph, text, font=LABEL_FONT, size=size, underline=True)
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


def _signer(cell, signer: SlipSigner | None, comment_size: float = PEN_SIZE) -> None:
    """One signed opinion box: the comment, the signature, the date and the name."""
    if signer is None:
        return
    # The comment's lines are set by the data ("\n"), so both heads' boxes break the same way
    # (owner, 13 Nov 2026: "both 3 lines and look the same"), written like the paper: from the
    # left, the first line indented. 1.2 lines so the tall pen letters are not cut.
    comment = _tight(cell.add_paragraph(), align=WD_ALIGN_PARAGRAPH.LEFT, line=1.2)
    fmt = comment.paragraph_format
    fmt.left_indent = fmt.right_indent = Cm(-PEN_BLEED_CM)  # into the cell's padding
    fmt.first_line_indent = Cm(PEN_INDENT_CM)
    lines = signer.comment.split("\n")
    for number, line in enumerate(lines):
        run = _run(comment, line, font=PEN_FONT, size=comment_size, color=INK_BLUE)
        if number < len(lines) - 1:
            run.add_break()
    if signer.signature is not None:
        picture = _tight(cell.add_paragraph(), align=WD_ALIGN_PARAGRAPH.CENTER)
        picture.add_run().add_picture(str(signer.signature), width=_picture_cm(2.6))
    date_line = _tight(cell.add_paragraph(), align=WD_ALIGN_PARAGRAPH.CENTER)
    _run(date_line, signer.date, font=PEN_FONT, size=PEN_SIZE, color=INK_BLUE)
    name = _tight(cell.add_paragraph(), align=WD_ALIGN_PARAGRAPH.CENTER, line=1.3)
    _run(name, f"{signer.title} {signer.name}".strip(), font=LABEL_FONT, size=10.5)


def _header(document) -> None:
    table = _plain_table(document, 1, [8.2, 10.7])
    brand, motto = table.rows[0].cells
    logo = _tight(_first(brand), align=WD_ALIGN_PARAGRAPH.CENTER)
    logo.add_run().add_picture(str(LOGO), width=_picture_cm(2.4))
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


def _timetable(cell, data: SlipData) -> None:
    """One session a row; a long booking two sessions a row, in the short form."""
    head = ("ល.រ", "កាលបរិច្ឆេទ", "វេលាម៉ោង")
    if len(data.timetable) < TWO_PER_ROW_FROM:
        lines, widths, size = [head, *data.timetable], (1.1, 6.0, 4.6), 9.5
    else:
        short = data.timetable_short
        half = math.ceil(len(short) / 2)
        pairs = [
            short[i] + (short[i + half] if i + half < len(short) else ("", "", ""))
            for i in range(half)
        ]
        lines, widths, size = [head + head, *pairs], (0.75, 2.75, 2.45) * 2, 8.5
    table = cell.add_table(rows=len(lines), cols=len(widths))
    table.style = "Table Grid"
    table.autofit = False
    _cell_padding(table, 0.06)
    for row, values in zip(table.rows, lines, strict=True):
        for box, width, value in zip(row.cells, widths, values, strict=True):
            box.width = Cm(width)
            _run(_tight(_first(box), line=1.0), value, size=size)
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
    _label(rows[3][0], f"មតិ{director}", box_cm=LEFT_BOX_CM)
    _signer(rows[3][0], data.director)
    text = rows[3][1]
    _ruled(text, f"៖ {data.subject}", new=False)
    if data.timetable:
        _timetable(text, data)
        _ruled(text, data.people_line, indent_cm=0.35)
    _ruled(text, "ស្នើសុំរៀបចំ៖", indent_cm=0.35)
    for line in data.requests:
        _ruled(text, line, indent_cm=0.35)
    if not data.timetable:
        _ruled(text, "", indent_cm=0.35)  # the paper's spare line; a timetable needs the room

    # The department head's box starts beside the closing lines and runs down the left, with
    # the dates, the office head's box and the booker on its right, as on the paper.
    _tight(_first(rows[4][0]), line=1.25)
    _label(rows[4][0], f"មតិ{data.department_head_title}ប្រធាននាយកដ្ឋាន", box_cm=LEFT_BOX_CM)
    _signer(rows[4][0], data.department_head, heads_comment_size(data))
    _ruled(rows[4][1], data.closing[0], first_line_cm=1.1, new=False)
    _ruled(rows[4][1], data.closing[1])
    _bottom(rows[4][1], data)


def _bottom(cell, data: SlipData) -> None:
    for number, line in enumerate((data.lunar_line, data.city_date)):
        dates = _tight(cell.add_paragraph(), align=WD_ALIGN_PARAGRAPH.RIGHT, line=1.3)
        dates.paragraph_format.space_before = _pt(6 if number == 0 else 0)
        _run(dates, line)
    table = _plain_table(cell, 1, [MIDDLE_CM - 0.2, RIGHT_CM - 0.2])
    _tiny(cell.paragraphs[-1])
    office, maker = table.rows[0].cells
    _label(
        _first(office), f"មតិ{data.office_head_title}ប្រធានការិយាល័យ", new=False, box_cm=OFFICE_BOX_CM
    )
    _signer(office, data.office_head, heads_comment_size(data))
    centre = WD_ALIGN_PARAGRAPH.CENTER
    _run(_tight(_first(maker), align=centre), "អ្នកធ្វើប័ណ្ណ")
    signature = _tight(maker.add_paragraph(), align=centre)
    if data.maker.signature is not None:
        signature.add_run().add_picture(str(data.maker.signature), width=_picture_cm(2.8))
    else:
        _tight(maker.add_paragraph())  # room to sign by hand
        _tight(maker.add_paragraph())
    _run(_tight(maker.add_paragraph(), align=centre, line=1.5), data.maker.name, font=LABEL_FONT)


def render_slip_docx(data: SlipData, scale: float | None = None) -> bytes:
    """The slip as .docx bytes. `scale` None: as large as fits one page (`fit_scale`)."""
    token = _scale.set(scale if scale is not None else fit_scale(data))
    try:
        return _render(data)
    finally:
        _scale.reset(token)


def _render(data: SlipData) -> bytes:
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


# --- Always one page ------------------------------------------------------------------------
# Measured in Word (13 Nov 2026) at scale 1.0 with the fonts above: a ruled line, a timetable row
# (one or two sessions to a row), and the rest of the slip, which does not change with the
# booking. A4 leaves 271 mm between the margins. The estimate errs high, so a slip shrinks a
# little more than it must, never less.
PAGE_MM = 271.0
LINE_MM = 9.5
ROW_MM = 6.6
TWO_ROW_MM = 5.8
FIXED_MM = 179.0
TABLE_MM = 5.0  # the space around the timetable
WIDTH_PER_LINE = 38.0  # Word fits about 40 Khmer letters on a ruled line
SMALLEST = 0.55


def _width(text: str) -> float:
    """How wide `text` prints, in Khmer letters: marks above or below a letter and a subscript
    letter (after ្) take no width; a space or a Latin letter takes less."""
    width, subscript = 0.0, False
    for char in text:
        if char == "្":
            subscript = True
        elif subscript:
            subscript = False
        elif unicodedata.category(char) == "Mn":
            continue
        else:
            width += 0.4 if char == " " else 0.6 if char < "Ā" else 1.0
    return width


def _lines(text: str, first_line: float = 0) -> int:
    """How many ruled lines `text` takes: words wrap at spaces; a long word breaks anywhere."""
    lines, used = 1, first_line
    for word in text.split(" "):
        size = _width(word) + (0.4 if used else 0)
        if used + size <= WIDTH_PER_LINE:
            used += size
            continue
        lines += 1
        used = _width(word)
        while used > WIDTH_PER_LINE:
            lines += 1
            used -= WIDTH_PER_LINE
    return lines


def content_mm(data: SlipData) -> float:
    """About how tall the slip is at scale 1.0."""
    ruled = (
        _lines(f"៖ - {data.department_line}")
        + _lines(f"- {data.office_line}", 1.5)
        + _lines(f"៖ {data.subject}")
        + 1  # ស្នើសុំរៀបចំ៖
        + len(data.requests)
    )
    if not data.timetable:
        return FIXED_MM + LINE_MM * (ruled + 1)  # + the paper's spare line
    rows = len(data.timetable)
    table = (
        (rows + 1) * ROW_MM if rows < TWO_PER_ROW_FROM else (math.ceil(rows / 2) + 1) * TWO_ROW_MM
    )
    return FIXED_MM + LINE_MM * (ruled + _lines(data.people_line or "")) + TABLE_MM + table


# Measured in Word (13 Nov 2026), in cm per letter of `_width`: Khmer OS Freehand at 10 pt
# prints 0.29-0.32, Khmer OS Muol Light 0.29-0.30 (at 10 pt). Inside the cell padding the left
# boxes are about 6.2 cm wide and the office head's box 5.7 cm; a comment may run 0.15 cm into
# the padding on each side.
PEN_CM_PER_LETTER = 0.31
LABEL_CM_PER_LETTER = 0.31  # at 10 pt, like the pen
LEFT_BOX_CM = 6.2
OFFICE_BOX_CM = 5.7
PEN_BLEED_CM = 0.15
PEN_INDENT_CM = 1.2  # the first line of a comment


def _fit_size(lines: list[str], size: float, box_cm: float, cm_per_letter: float) -> float:
    """`size`, or smaller (in half points, 6.5 pt at least) so the longest line fits `box_cm`."""
    longest = max((_width(line) for line in lines), default=0.0) * cm_per_letter * size / 10
    if longest <= box_cm:
        return size
    return max(6.5, math.floor(size * box_cm / longest * 2) / 2)


def heads_comment_size(data: SlipData) -> float:
    """One pen size for both heads' comments, so the two boxes look the same: PEN_SIZE, or smaller
    when their longest line would not fit the narrower (office head's) box."""
    lines = [
        line
        for head in (data.department_head, data.office_head)
        if head is not None and head.comment
        for line in head.comment.split("\n")
    ]
    return _fit_size(lines, PEN_SIZE, OFFICE_BOX_CM + 2 * PEN_BLEED_CM, PEN_CM_PER_LETTER)


def fit_scale(data: SlipData) -> float:
    """How much to shrink this slip so it fits one A4 page (1.0 = no shrink)."""
    return max(SMALLEST, min(1.0, math.floor(PAGE_MM / content_mm(data) * 100) / 100))
