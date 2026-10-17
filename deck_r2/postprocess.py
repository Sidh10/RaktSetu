# Copied unchanged from RaktSetu_simulator_and_prototype/deck_v3/postprocess.py: Orbitron runs get small caps, as in v3.
import re, sys, zipfile, shutil, os
src = sys.argv[1]; tmp = src + ".tmp"
zin = zipfile.ZipFile(src); zout = zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED)
n = 0
for item in zin.infolist():
    data = zin.read(item.filename)
    if item.filename.startswith("ppt/slides/slide") and item.filename.endswith(".xml"):
        x = data.decode("utf8")
        def fix(m):
            global n
            seg = m.group(0)
            if 'typeface="Orbitron"' in seg and ' cap=' not in seg.split('>')[0]:
                n += 1
                return seg.replace("<a:rPr", '<a:rPr cap="small"', 1)
            return seg
        x = re.sub(r"<a:rPr\b[^>]*?(?:/>|>.*?</a:rPr>)", fix, x, flags=re.S)
        data = x.encode("utf8")
    zout.writestr(item, data)
zout.close(); shutil.move(tmp, src); print("small caps runs:", n)
