from PIL import Image

for page in (3, 5, 6, 7):
    source = Image.open(rf".codex_tmp\framework_pngs_v2\page-{page}.png")
    crop = source.crop((100, 430, 1150, 570))
    crop.save(rf".codex_tmp\framework_pngs_v2\crop-{page}.png")
