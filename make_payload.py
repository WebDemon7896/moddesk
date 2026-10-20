"""make_payload.py FOLDER OUT.zip - zip a folder with forward-slash names (PowerShell's Compress-Archive uses backslashes)."""
import os
import sys
import zipfile

src, out = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for root, _dirs, files in os.walk(src):
        for f in files:
            full = os.path.join(root, f)
            z.write(full, os.path.relpath(full, src).replace(os.sep, "/"))
print("payload:", out)
