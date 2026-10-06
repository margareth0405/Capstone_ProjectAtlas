from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "artifacts"
QA_DIR = ROOT / ".codex_tmp" / "framework_assets"
OUT_DIR.mkdir(exist_ok=True)
QA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT = OUT_DIR / "ATLAS_Conceptual_Framework_Role_Flows.docx"

NAVY = "0B2545"
BLUE = "2E74B5"
DARK_BLUE = "1F4D78"
MAROON = "7A1F32"
TEAL = "1E6F6D"
GOLD = "B4862B"
INK = "172033"
MUTED = "5E6878"
LIGHT_BLUE = "E8EEF5"
LIGHT_GRAY = "F2F4F7"
PALE_GOLD = "FBF5E7"
PALE_TEAL = "E9F5F3"
PALE_MAROON = "F7EAED"
WHITE = "FFFFFF"
BORDER = "CDD6E3"

FONT_REG = r"C:\Windows\Fonts\calibri.ttf"
FONT_BOLD = r"C:\Windows\Fonts\calibrib.ttf"


def rgb(hex_color):
    return RGBColor.from_string(hex_color)


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=100, start=120, bottom=100, end=120):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_table_geometry(table, widths_dxa, indent_dxa=120):
    total = sum(widths_dxa)
    table.autofit = False
    tbl_pr = table._tbl.tblPr
    layout = tbl_pr.find(qn("w:tblLayout"))
    if layout is None:
        layout = OxmlElement("w:tblLayout")
        tbl_pr.append(layout)
    layout.set(qn("w:type"), "fixed")
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(total))
    tbl_w.set(qn("w:type"), "dxa")
    tbl_ind = tbl_pr.find(qn("w:tblInd"))
    if tbl_ind is None:
        tbl_ind = OxmlElement("w:tblInd")
        tbl_pr.append(tbl_ind)
    tbl_ind.set(qn("w:w"), str(indent_dxa))
    tbl_ind.set(qn("w:type"), "dxa")

    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths_dxa:
        col = OxmlElement("w:gridCol")
        col.set(qn("w:w"), str(width))
        grid.append(col)

    for row in table.rows:
        for idx, cell in enumerate(row.cells):
            width = widths_dxa[idx]
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_w = tc_pr.find(qn("w:tcW"))
            if tc_w is None:
                tc_w = OxmlElement("w:tcW")
                tc_pr.append(tc_w)
            tc_w.set(qn("w:w"), str(width))
            tc_w.set(qn("w:type"), "dxa")
            cell.width = Inches(width / 1440)
            set_cell_margins(cell)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER


def set_table_borders(table, color=BORDER, size=6):
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = borders.find(qn(f"w:{edge}"))
        if tag is None:
            tag = OxmlElement(f"w:{edge}")
            borders.append(tag)
        tag.set(qn("w:val"), "single")
        tag.set(qn("w:sz"), str(size))
        tag.set(qn("w:space"), "0")
        tag.set(qn("w:color"), color)


def set_run(run, size=11, color=INK, bold=False, italic=False, font="Calibri"):
    run.font.name = font
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), font)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), font)
    run.font.size = Pt(size)
    run.font.color.rgb = rgb(color)
    run.bold = bold
    run.italic = italic
    return run


def set_paragraph_spacing(p, before=0, after=6, line=1.25, keep_with_next=False):
    fmt = p.paragraph_format
    fmt.space_before = Pt(before)
    fmt.space_after = Pt(after)
    fmt.line_spacing = line
    fmt.keep_with_next = keep_with_next


def add_numbering_definition(doc, bullet=False):
    numbering = doc.part.numbering_part.element
    abstract_ids = [int(x.get(qn("w:abstractNumId"))) for x in numbering.findall(qn("w:abstractNum"))]
    num_ids = [int(x.get(qn("w:numId"))) for x in numbering.findall(qn("w:num"))]
    abstract_id = max(abstract_ids, default=0) + 1
    num_id = max(num_ids, default=0) + 1

    abstract = OxmlElement("w:abstractNum")
    abstract.set(qn("w:abstractNumId"), str(abstract_id))
    multi = OxmlElement("w:multiLevelType")
    multi.set(qn("w:val"), "singleLevel")
    abstract.append(multi)
    lvl = OxmlElement("w:lvl")
    lvl.set(qn("w:ilvl"), "0")
    start = OxmlElement("w:start")
    start.set(qn("w:val"), "1")
    lvl.append(start)
    num_fmt = OxmlElement("w:numFmt")
    num_fmt.set(qn("w:val"), "bullet" if bullet else "decimal")
    lvl.append(num_fmt)
    lvl_text = OxmlElement("w:lvlText")
    lvl_text.set(qn("w:val"), "\uf0b7" if bullet else "%1.")
    lvl.append(lvl_text)
    suff = OxmlElement("w:suff")
    suff.set(qn("w:val"), "tab")
    lvl.append(suff)
    p_pr = OxmlElement("w:pPr")
    tabs = OxmlElement("w:tabs")
    tab = OxmlElement("w:tab")
    tab.set(qn("w:val"), "num")
    tab.set(qn("w:pos"), "540")
    tabs.append(tab)
    p_pr.append(tabs)
    ind = OxmlElement("w:ind")
    ind.set(qn("w:left"), "540")
    ind.set(qn("w:hanging"), "270")
    p_pr.append(ind)
    spacing = OxmlElement("w:spacing")
    spacing.set(qn("w:after"), "80")
    spacing.set(qn("w:line"), "300")
    spacing.set(qn("w:lineRule"), "auto")
    p_pr.append(spacing)
    lvl.append(p_pr)
    if bullet:
        r_pr = OxmlElement("w:rPr")
        r_fonts = OxmlElement("w:rFonts")
        r_fonts.set(qn("w:ascii"), "Symbol")
        r_fonts.set(qn("w:hAnsi"), "Symbol")
        r_fonts.set(qn("w:hint"), "default")
        r_pr.append(r_fonts)
        lvl.append(r_pr)
    abstract.append(lvl)
    numbering.append(abstract)

    num = OxmlElement("w:num")
    num.set(qn("w:numId"), str(num_id))
    abstract_ref = OxmlElement("w:abstractNumId")
    abstract_ref.set(qn("w:val"), str(abstract_id))
    num.append(abstract_ref)
    numbering.append(num)
    return num_id


def configure_builtin_bullets(doc, num_id=1):
    """Keep Word's native bullet glyph while applying the compact preset spacing."""

    numbering = doc.part.numbering_part.element
    num = next(
        node
        for node in numbering.findall(qn("w:num"))
        if node.get(qn("w:numId")) == str(num_id)
    )
    abstract_id = num.find(qn("w:abstractNumId")).get(qn("w:val"))
    abstract = next(
        node
        for node in numbering.findall(qn("w:abstractNum"))
        if node.get(qn("w:abstractNumId")) == abstract_id
    )
    level = next(
        node
        for node in abstract.findall(qn("w:lvl"))
        if node.get(qn("w:ilvl")) == "0"
    )
    p_pr = level.find(qn("w:pPr"))
    if p_pr is None:
        p_pr = OxmlElement("w:pPr")
        level.append(p_pr)
    ind = p_pr.find(qn("w:ind"))
    if ind is None:
        ind = OxmlElement("w:ind")
        p_pr.append(ind)
    ind.set(qn("w:left"), "540")
    ind.set(qn("w:hanging"), "270")
    spacing = p_pr.find(qn("w:spacing"))
    if spacing is None:
        spacing = OxmlElement("w:spacing")
        p_pr.append(spacing)
    spacing.set(qn("w:after"), "80")
    spacing.set(qn("w:line"), "300")
    spacing.set(qn("w:lineRule"), "auto")
    return num_id


def add_list_item(doc, text, num_id, bold_lead=None):
    p = doc.add_paragraph(style="List Bullet")
    set_paragraph_spacing(p, after=4, line=1.25)
    if bold_lead and text.startswith(bold_lead):
        set_run(p.add_run(bold_lead), bold=True)
        set_run(p.add_run(text[len(bold_lead):]))
    else:
        set_run(p.add_run(text))
    return p


def add_heading(doc, text, level=1):
    p = doc.add_paragraph(style=f"Heading {level}")
    p.add_run(text)
    return p


def add_label_paragraph(doc, label, text, after=6):
    p = doc.add_paragraph(style="Normal")
    set_paragraph_spacing(p, after=after)
    set_run(p.add_run(label + " "), bold=True, color=DARK_BLUE)
    set_run(p.add_run(text))
    return p


def add_callout(doc, title, text, fill=LIGHT_BLUE, accent=BLUE):
    table = doc.add_table(rows=1, cols=1)
    set_table_geometry(table, [9360], 120)
    set_table_borders(table, color=accent, size=8)
    cell = table.cell(0, 0)
    set_cell_shading(cell, fill)
    p = cell.paragraphs[0]
    set_paragraph_spacing(p, after=0, line=1.15)
    set_run(p.add_run(title + " "), size=10.5, bold=True, color=accent)
    set_run(p.add_run(text), size=10.5, color=INK)
    spacer = doc.add_paragraph()
    set_paragraph_spacing(spacer, after=2)
    return table


def add_picture_with_alt(doc, path, width_inches, alt_text, caption=None):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_paragraph_spacing(p, before=4, after=5, line=1.0)
    run = p.add_run()
    shape = run.add_picture(str(path), width=Inches(width_inches))
    doc_pr = shape._inline.docPr
    doc_pr.set("descr", alt_text)
    doc_pr.set("title", caption or "ATLAS system flow diagram")
    if caption:
        cap = doc.add_paragraph(style="Caption")
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_paragraph_spacing(cap, before=0, after=8, line=1.0)
        set_run(cap.add_run(caption), size=9, color=MUTED, italic=True)
    return p


def rounded_box(draw, xy, fill, outline, title, body, title_color=WHITE, body_color=INK):
    def pil_color(value):
        return value if value.startswith("#") else f"#{value}"

    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(
        xy,
        radius=22,
        fill=pil_color(fill),
        outline=pil_color(outline),
        width=4,
    )
    title_font = ImageFont.truetype(FONT_BOLD, 30)
    body_font = ImageFont.truetype(FONT_REG, 24)
    title_lines = wrap(title, width=18)
    y = y1 + 18
    for line in title_lines:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        draw.text(((x1+x2-bbox[2])/2, y), line, font=title_font, fill=pil_color(title_color))
        y += 34
    y += 8
    for line in wrap(body, width=23):
        bbox = draw.textbbox((0, 0), line, font=body_font)
        draw.text(((x1+x2-bbox[2])/2, y), line, font=body_font, fill=pil_color(body_color))
        y += 29


def arrow(draw, start, end, color="#667085", width=7):
    draw.line([start, end], fill=color, width=width)
    ex, ey = end
    sx, sy = start
    if abs(ex-sx) >= abs(ey-sy):
        direction = 1 if ex > sx else -1
        pts = [(ex, ey), (ex-18*direction, ey-12), (ex-18*direction, ey+12)]
    else:
        direction = 1 if ey > sy else -1
        pts = [(ex, ey), (ex-12, ey-18*direction), (ex+12, ey-18*direction)]
    draw.polygon(pts, fill=color)


def make_overall_flow(path):
    img = Image.new("RGB", (1500, 720), "white")
    d = ImageDraw.Draw(img)
    title = ImageFont.truetype(FONT_BOLD, 38)
    d.text((50, 30), "ATLAS entry and role-routing flow", font=title, fill="#0B2545")
    rounded_box(d, (530, 105, 970, 225), "#0B2545", "#0B2545", "Visitor reaches ATLAS", "Landing page", WHITE, WHITE)
    d.line((750, 225, 750, 280), fill="#667085", width=7)
    d.line((250, 280, 1250, 280), fill="#667085", width=7)
    for x in (250, 750, 1250):
        arrow(d, (x, 280), (x, 325))
    rounded_box(d, (55, 325, 445, 470), "#B4862B", "#8D681D", "Guest", "Continue without an account", WHITE, WHITE)
    rounded_box(d, (555, 325, 945, 470), "#2E74B5", "#1F4D78", "Student or Teacher", "Use the selected-role form", WHITE, WHITE)
    rounded_box(d, (1055, 325, 1445, 470), "#7A1F32", "#5C1525", "Administrator or Superuser", "Private staff sign-in", WHITE, WHITE)
    arrow(d, (250, 470), (250, 535))
    arrow(d, (750, 470), (750, 535))
    arrow(d, (1250, 470), (1250, 535))
    rounded_box(d, (55, 535, 445, 675), "#FBF5E7", "#B4862B", "Guest workspace", "Browse public Digital Sources", NAVY, INK)
    rounded_box(d, (555, 535, 945, 675), "#E8EEF5", "#2E74B5", "Role-aware workspace", "Reader or Teacher tools", NAVY, INK)
    rounded_box(d, (1055, 535, 1445, 675), "#F7EAED", "#7A1F32", "Staff workspace", "Tools based on staff level", NAVY, INK)
    img.save(path, quality=95)


def make_ipo_flow(path):
    img = Image.new("RGB", (1500, 560), "white")
    d = ImageDraw.Draw(img)
    title = ImageFont.truetype(FONT_BOLD, 38)
    d.text((50, 30), "Conceptual framework: Input → Process → Output → Outcome", font=title, fill="#0B2545")
    boxes = [
        ("INPUT", "Role, credentials or guest choice; privacy consent; search or management request", "#2E74B5"),
        ("PROCESS", "Authenticate or open guest session; determine role; enforce permissions; process request", "#1E6F6D"),
        ("OUTPUT", "Role-specific dashboard, Digital Sources results, saved changes, reports or messages", "#7A1F32"),
        ("OUTCOME", "Secure and equitable access, reliable repository management, accountable activity", "#B4862B"),
    ]
    x_positions = [45, 415, 785, 1155]
    for idx, (heading, body, color) in enumerate(boxes):
        x = x_positions[idx]
        rounded_box(d, (x, 150, x+300, 465), color, color, heading, body, WHITE, WHITE)
        if idx < len(boxes)-1:
            arrow(d, (x+300, 307), (x_positions[idx+1]-25, 307), width=8)
    img.save(path, quality=95)


def make_role_flow(path, role, color, steps):
    img = Image.new("RGB", (1500, 350), "white")
    d = ImageDraw.Draw(img)
    title = ImageFont.truetype(FONT_BOLD, 38)
    d.text((45, 25), f"{role} flow", font=title, fill="#0B2545")
    n = len(steps)
    left = 40
    gap = 35
    box_w = int((1420 - gap*(n-1)) / n)
    for idx, (heading, body) in enumerate(steps):
        x1 = left + idx*(box_w+gap)
        x2 = x1 + box_w
        rounded_box(d, (x1, 105, x2, 315), color, color, heading, body, WHITE, WHITE)
        if idx < n-1:
            arrow(d, (x2, 210), (x2+gap-8, 210), width=6)
    img.save(path, quality=95)


def add_role_section(doc, title, role_label, color, diagram, entry, actions, restrictions, result):
    add_heading(doc, title, 1)
    add_picture_with_alt(
        doc,
        diagram,
        6.35,
        f"Sequential {role_label} flow from entry through role-specific actions to completion.",
        f"Figure: {role_label} workflow",
    )
    add_label_paragraph(doc, "Entry and identity.", entry)
    p = doc.add_paragraph(style="Normal")
    set_paragraph_spacing(p, after=2)
    set_run(p.add_run("Main actions"), bold=True, color=DARK_BLUE)
    for action in actions:
        add_list_item(doc, action, BULLET_NUM_ID)
    add_label_paragraph(doc, "Boundary.", restrictions)
    add_label_paragraph(doc, "End state.", result, after=8)


doc = Document()
section = doc.sections[0]
section.page_width = Inches(8.5)
section.page_height = Inches(11)
section.top_margin = Inches(1)
section.right_margin = Inches(1)
section.bottom_margin = Inches(1)
section.left_margin = Inches(1)
section.header_distance = Inches(0.492)
section.footer_distance = Inches(0.492)

# Resolve compact_reference_guide preset tokens explicitly.
styles = doc.styles
normal = styles["Normal"]
normal.font.name = "Calibri"
normal._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
normal.font.size = Pt(11)
normal.font.color.rgb = rgb(INK)
normal.paragraph_format.space_before = Pt(0)
normal.paragraph_format.space_after = Pt(6)
normal.paragraph_format.line_spacing = 1.25

heading_tokens = {
    "Heading 1": (16, BLUE, 18, 10),
    "Heading 2": (13, BLUE, 14, 7),
    "Heading 3": (12, DARK_BLUE, 10, 5),
}
for name, (size, color, before, after) in heading_tokens.items():
    style = styles[name]
    style.font.name = "Calibri"
    style._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
    style._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
    style.font.size = Pt(size)
    style.font.bold = True
    style.font.color.rgb = rgb(color)
    style.paragraph_format.space_before = Pt(before)
    style.paragraph_format.space_after = Pt(after)
    style.paragraph_format.keep_with_next = True

caption_style = styles["Caption"]
caption_style.font.name = "Calibri"
caption_style._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
caption_style._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
caption_style.font.size = Pt(9)
caption_style.font.italic = True
caption_style.font.color.rgb = rgb(MUTED)

bullet_style = styles["List Bullet"]
bullet_style.font.name = "Calibri"
bullet_style._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
bullet_style._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
bullet_style.font.size = Pt(11)
bullet_style.font.color.rgb = rgb(INK)
bullet_style.paragraph_format.left_indent = Inches(0.375)
bullet_style.paragraph_format.first_line_indent = Inches(-0.1875)
bullet_style.paragraph_format.space_after = Pt(4)
bullet_style.paragraph_format.line_spacing = 1.25

BULLET_NUM_ID = None

# Running header and footer.
header = section.header
hp = header.paragraphs[0]
hp.alignment = WD_ALIGN_PARAGRAPH.LEFT
set_paragraph_spacing(hp, after=0, line=1.0)
set_run(hp.add_run("ATLAS | CONCEPTUAL FRAMEWORK"), size=8.5, bold=True, color=MUTED)

footer = section.footer
fp = footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
set_run(fp.add_run("ATLAS | ROLE-BASED SYSTEM FLOW"), size=8.5, color=MUTED)

# Diagrams.
overall_path = QA_DIR / "overall_flow.png"
ipo_path = QA_DIR / "ipo_framework.png"
make_overall_flow(overall_path)
make_ipo_flow(ipo_path)

role_diagrams = {}
role_specs = {
    "Guest": (GOLD, [
        ("Open ATLAS", "Reach the landing page"),
        ("Choose Guest", "Start a guest session"),
        ("Explore", "Browse and filter Digital Sources"),
        ("Read", "View details and protected abstract"),
        ("Finish", "Contact support or leave"),
    ]),
    "Student": (BLUE, [
        ("Choose Student", "Register or sign in"),
        ("Verify", "Match Student role and consent"),
        ("Explore", "Search and filter resources"),
        ("Save", "Bookmark useful items"),
        ("Continue", "Read, contact, or sign out"),
    ]),
    "Teacher": (TEAL, [
        ("Upload", "Teacher submits resource"),
        ("AI analysis", "Automatic screening"),
        ("Pending", "Private review queue"),
        ("Staff review", "Administrator checks"),
        ("Approve", "Decision is recorded"),
        ("Publish", "Readers can discover it"),
    ]),
    "Administrator": (MAROON, [
        ("Private sign-in", "Use staff credentials"),
        ("Staff portal", "Open administration home"),
        ("Manage", "Readers, resources, announcements"),
        ("Monitor", "Usage, resource views, activity"),
        ("Close", "Save logged action and sign out"),
    ]),
    "Superuser": (NAVY, [
        ("Private sign-in", "Use root credentials"),
        ("Full staff access", "Use all admin workspaces"),
        ("Govern admins", "Create, edit, or delete Administrators"),
        ("Oversee system", "Review reports and configuration"),
        ("Close", "Audit changes and sign out"),
    ]),
}
for role, (color, steps) in role_specs.items():
    path = QA_DIR / f"{role.lower()}_flow.png"
    make_role_flow(path, role, color, steps)
    role_diagrams[role] = path

# Cover / opening block using the editorial-cover pattern.
p = doc.add_paragraph()
set_paragraph_spacing(p, before=30, after=12)
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
set_run(p.add_run("SYSTEM CONCEPTUAL FRAMEWORK"), size=11, bold=True, color=GOLD)
p = doc.add_paragraph()
set_paragraph_spacing(p, after=8)
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
set_run(p.add_run("ATLAS Role-Based System Flow"), size=30, bold=True, color=NAVY)
p = doc.add_paragraph()
set_paragraph_spacing(p, after=6)
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
set_run(p.add_run("Superuser, Administrator, Teacher, Student User, and Guest"), size=15, color=DARK_BLUE)
p = doc.add_paragraph()
set_paragraph_spacing(p, after=20)
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
set_run(p.add_run("Prepared from the current ATLAS implementation • 6 October 2026"), size=9.5, italic=True, color=MUTED)

add_callout(
    doc,
    "Scope note.",
    "In this framework, “User” means the registered Student role. Teacher is shown separately because it has additional resource-management and AI-review privileges. Guest means an unauthenticated visitor using guest access.",
    fill=PALE_GOLD,
    accent=GOLD,
)
add_picture_with_alt(
    doc,
    overall_path,
    6.35,
    "ATLAS entry flow branches from the landing page to Guest access, Student or Teacher role-aware authentication, or private Administrator and Superuser authentication.",
    "Figure 1. Entry and role-routing flow",
)

doc.add_page_break()
add_heading(doc, "1. Conceptual Framework", 1)
add_label_paragraph(
    doc,
    "Framework logic.",
    "ATLAS receives a role and a request, validates the permitted path, performs the requested repository or administrative operation, and returns an output appropriate to that role. Every privileged branch is narrower than the branch above it unless the role is explicitly granted more authority.",
)
add_picture_with_alt(
    doc,
    ipo_path,
    6.35,
    "Input-Process-Output-Outcome framework for ATLAS: identity and request inputs are authenticated and authorized, producing role-specific results and secure repository outcomes.",
    "Figure 2. Input-Process-Output-Outcome model",
)

add_heading(doc, "Core control principles", 2)
for item in [
    "Role-aware entry: Student and Teacher use the public role-based registration and login flow; staff use the private administration route.",
    "Least privilege: Student and Guest are readers, Teacher submits resources for review, Administrator manages operations and publication review, and Superuser governs Administrators.",
    "Protected reading: resource abstracts are displayed inside ATLAS; the original uploaded file is not offered as a public download.",
    "Accountability: important creation, update, deletion, analysis, and administrative events can be retained for staff reporting and audit review.",
    "Privacy-aware usage: signed-in activity supports institutional reporting, while anonymous guest analytics depend on the visitor's analytics consent.",
]:
    add_list_item(doc, item, BULLET_NUM_ID)

add_callout(
    doc,
    "Role chain.",
    "Guest explores; Student saves; Teacher contributes; Administrator operates; Superuser governs. Each step adds only the authority needed for that role.",
    fill=LIGHT_BLUE,
    accent=BLUE,
)

doc.add_page_break()
add_role_section(
    doc,
    "2. Guest Flow",
    "Guest",
    GOLD,
    role_diagrams["Guest"],
    "The visitor opens ATLAS and selects Guest. The system creates a guest session and opens the reader dashboard without requiring an account.",
    [
        "View the dashboard and public announcements.",
        "Browse, search, filter, and sort Digital Sources.",
        "Open resource details, see hard-copy availability, and read the protected resource abstract.",
        "Submit a support, feedback, or privacy-related contact message.",
        "Choose cookie preferences; anonymous usage analytics are stored only with analytics consent.",
    ],
    "A Guest cannot bookmark items, manage Digital Sources, use AI Detection, open staff reports, or administer accounts.",
    "The visitor leaves the site or later chooses Student or Teacher registration/sign-in for persistent account features.",
)

doc.add_page_break()
add_heading(doc, "3. Student (Registered User) Flow", 1)
add_picture_with_alt(
    doc,
    role_diagrams["Student"],
    6.35,
    "Student flow from role selection and registration or login through browsing, bookmarking, reading, and sign-out.",
    "Figure: Student workflow",
)
add_label_paragraph(doc, "Entry and identity.", "The visitor selects Student, registers or signs in with email and password, accepts the current privacy terms, and passes role matching and email verification requirements.")
p = doc.add_paragraph(style="Normal")
set_paragraph_spacing(p, after=2)
set_run(p.add_run("Main actions"), bold=True, color=DARK_BLUE)
for action in [
    "Use the personalized dashboard and scroll through Recently Added Digital Sources; announcements remain available on their dedicated scrollable page.",
    "Search, filter, sort, and open repository items.",
    "Read protected resource abstracts and check hard-copy availability.",
    "Bookmark or remove resources and open the Favorites page.",
    "Update account email/password settings, contact support, or submit a data-deletion request.",
]:
    add_list_item(doc, action, BULLET_NUM_ID)
add_label_paragraph(doc, "Boundary.", "A Student cannot add, edit, or delete resources; cannot use AI Detection; and cannot access staff account, announcement, reporting, or Django administration tools.")
add_label_paragraph(doc, "End state.", "The Student's bookmarks and account settings persist for the next session; signing out returns the user to the public landing page.", after=8)

doc.add_page_break()
add_role_section(
    doc,
    "4. Teacher Flow",
    "Teacher",
    TEAL,
    role_diagrams["Teacher"],
    "The visitor selects Teacher, registers or signs in through the public role-aware form, accepts the privacy terms, and passes Teacher-role and email verification checks.",
    [
        "Perform every normal reader activity: browse, search, view details, read abstracts, bookmark, and contact support.",
        "Upload a Digital Sources item with metadata, cover image, resource abstract, resource file, and hard-copy availability information.",
        "ATLAS automatically analyzes the uploaded resource abstract and records a privacy-safe screening summary.",
        "The submission enters Pending Review and remains hidden from Students and Guests until a staff reviewer approves it.",
        "Edit or delete Digital Sources items; a Teacher edit returns the resource to Pending Review and runs the analysis again.",
        "Use the separate AI Detection tool on pasted text or an uploaded supported document and review the advisory result.",
        "Update the Teacher display name and normal account credentials.",
    ],
    "A Teacher is not a staff Administrator. The role cannot manage users, create announcements, publish content notices, view staff usage/audit reports, open the staff portal, or access Django administration.",
    "After approval by an Administrator or Superuser, the resource is marked Approved and becomes published in Digital Sources. A rejected submission remains visible to its Teacher for correction but stays private from Students and Guests.",
)
add_callout(
    doc,
    "AI result caution.",
    "AI Detection is an advisory writing-pattern review. Its result should support human review and should not be treated as sole proof for an academic or disciplinary decision.",
    fill=PALE_TEAL,
    accent=TEAL,
)

doc.add_page_break()
add_role_section(
    doc,
    "5. Administrator Flow",
    "Administrator",
    MAROON,
    role_diagrams["Administrator"],
    "The Administrator does not use the public Student/Teacher login. The account signs in through the private Django administration route using an active staff username or email and password.",
    [
        "Open the Administrator Home and the normal Django administration pages allowed by staff permissions.",
        "Create immediately verified Student or Teacher accounts for live testing, search/filter the user directory, and delete non-staff reader accounts.",
        "Review Teacher submissions and their AI screening summaries, then approve and publish them or request changes.",
        "Manage Digital Sources and use the separate AI Detection tool.",
        "Draft, edit, publish, unpublish, and delete announcements.",
        "Review website usage, role activity, resource views, unresolved messages, and the administrative activity log.",
        "Change the Administrator's own username or password.",
    ],
    "A regular Administrator cannot create another Administrator, cannot manage another staff account's credentials, and cannot exercise Superuser-only governance. Direct access to Superuser-only actions is denied.",
    "Operational changes are saved and recorded where applicable. Staff sign-out returns to the private administration login instead of the public role selector.",
)

doc.add_page_break()
add_role_section(
    doc,
    "6. Superuser Flow",
    "Superuser",
    NAVY,
    role_diagrams["Superuser"],
    "The Superuser signs in through the same private administration route, but the system recognizes the account as the highest staff level.",
    [
        "Perform every Administrator operation across resources, users, announcements, AI Detection, reports, activity history, and Django administration.",
        "Create a regular Administrator after confirming the Superuser's own password.",
        "Edit or delete a regular Administrator account while protecting the active Superuser and every Superuser account from portal deletion.",
        "Review system-wide configuration, operational health, and audit evidence as the root authority.",
    ],
    "The Superuser retains the highest application authority and should use that access only for governance, security, and exceptional administration. Reader accounts remain separate from staff accounts.",
    "Administrator provisioning, deletion, and sensitive account changes are recorded, then the Superuser signs out to the private administration login.",
)

add_heading(doc, "7. Authority and Feedback Loop", 1)
add_label_paragraph(doc, "Hierarchy.", "Superuser, Administrator, Teacher, Student User, and Guest represent progressively narrower authority. This does not mean lower roles report directly to every higher role; each role receives only the tools needed for its purpose.")
for item in [
    "Guests and registered readers generate search, reading, bookmark, contact, and usage signals.",
    "Teachers submit repository content and receive AI-review outputs while remaining outside staff administration.",
    "Administrators review pending Teacher submissions, make the human publication decision, and use operational reports and messages to maintain the system.",
    "Superusers govern Administrator access and intervene in high-risk or system-level decisions.",
    "Published announcements and updated resources return to the reader-facing system, completing the feedback loop.",
]:
    add_list_item(doc, item, BULLET_NUM_ID)

add_callout(
    doc,
    "Conceptual summary.",
    "ATLAS separates public discovery, registered reading, teacher contribution, operational administration, and root governance. The system first identifies the role, then enforces the narrowest appropriate permission set before presenting features or saving changes.",
    fill=LIGHT_BLUE,
    accent=BLUE,
)

add_heading(doc, "Implementation alignment", 2)
for label, text in [
    ("Student/Teacher entry.", "Role-aware public registration and login keep reader identity and privacy consent aligned."),
    ("Guest entry.", "Session-based guest mode allows low-friction public exploration."),
    ("Teacher resource tools.", "A resource-manager permission check allows uploads and AI screening without staff authority; Teacher changes are private until staff approval."),
    ("Administrator tools.", "An active-staff permission check protects resource approval, user, announcement, and reporting functions."),
    ("Superuser governance.", "A Superuser-only permission check protects Administrator creation, credential management, and deletion."),
]:
    add_label_paragraph(doc, label, text, after=4)

# Core properties and final document settings.
doc.core_properties.title = "ATLAS Conceptual Framework and Role-Based System Flow"
doc.core_properties.subject = "Superuser, Administrator, Teacher, Student User, and Guest flows"
doc.core_properties.author = "ATLAS Project Team"
doc.core_properties.keywords = "ATLAS, conceptual framework, role flow, access control"

doc.save(OUTPUT)
# Re-open and save once so python-docx normalizes package relationships and
# element ordering after the low-level numbering/table additions above.
Document(OUTPUT).save(OUTPUT)
print(OUTPUT)
