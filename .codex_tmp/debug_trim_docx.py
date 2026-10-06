import sys

from docx import Document
from docx.oxml.ns import qn

source = r"artifacts\ATLAS_Conceptual_Framework_Role_Flows.docx"
break_limit = int(sys.argv[1]) if len(sys.argv) > 1 else 1
target = rf".codex_tmp\framework_first_{break_limit}_sections.docx"
doc = Document(source)
body = doc._element.body
seen_breaks = 0
for child in list(body):
    if seen_breaks >= break_limit and child.tag != qn("w:sectPr"):
        body.remove(child)
        continue
    if child.findall(".//" + qn("w:br")):
        seen_breaks += 1
        body.remove(child)
doc.save(target)
print(target)
