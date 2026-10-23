from pathlib import Path
from PIL import Image, ImageDraw

Path("assets").mkdir(exist_ok=True)
img = Image.new("RGBA", (256, 256), (5, 5, 5, 255))
d = ImageDraw.Draw(img)
for r, col in ((112, (120, 0, 0, 255)), (92, (225, 6, 0, 255)), (60, (255, 212, 0, 255))):
    d.ellipse((128 - r, 128 - r, 128 + r, 128 + r), fill=col)
img.save("assets/yavis.ico", sizes=[(256, 256), (64, 64), (32, 32), (16, 16)])
print("icon ok")
