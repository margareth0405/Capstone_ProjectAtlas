import sys

from docx import Document
from docx.oxml.ns import qn

cutoff = int(sys.argv[1])
source = r"artifacts\ATLAS_Conceptual_Framework_Role_Flows.docx"
target = rf".codex_tmp\framework_cut_{cutoff}.docx"
doc = Document(source)
body = doc._element.body
for index, child in enumerate(list(body)):
    if index > cutoff and child.tag != qn("w:sectPr"):
        body.remove(child)
doc.save(target)
print(target)
