from docling.document_converter import DocumentConverter
import os

source = "https://arxiv.org/pdf/2408.09869"  # document per local path or URL
output_dir = "./output"

converter = DocumentConverter()
result = converter.convert(source)

os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "f{test-docling-output.md}")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(result.document.export_to_markdown())

print(result.document.export_to_markdown())  # output: "## Docling Technical Report[...]"