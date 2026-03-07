# qr_gallery.py
import os

def build_qr_gallery():
    out_dir = "qr_exports"
    html_file = "qr_gallery2.html"

    # Collect all SVG files
    svg_files = [f for f in os.listdir(out_dir) if f.endswith(".svg")]

    if not svg_files:
        print("No SVG files found in qr_exports.")
        return

    # Build HTML content
    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='UTF-8'>",
        "<title>QR Code Gallery</title>",
        "<style>",
        "body { font-family: Arial, sans-serif; }",
        ".qr { display: inline-block; margin: 20px; text-align: center; }",
        ".qr svg { width: 200px; height: 200px; }",
        "</style>",
        "</head>",
        "<body>",
        "<h1>QR Code Gallery</h1>"
    ]

    for fname in svg_files:
        path = os.path.join(out_dir, fname)
        with open(path, "r", encoding="utf-8") as f:
            svg_content = f.read()
        html_parts.append("<div class='qr'>")
        html_parts.append(f"<h3>{fname}</h3>")
        html_parts.append(svg_content)  # embed raw SVG markup
        html_parts.append("</div>")

    html_parts.append("</body></html>")

    # Write HTML file
    with open(html_file, "w", encoding="utf-8") as f:
        f.write("\n".join(html_parts))

    print(f"QR gallery built → {html_file}")


if __name__ == "__main__":
    build_qr_gallery()
