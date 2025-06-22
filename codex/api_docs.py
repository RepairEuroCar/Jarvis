import os
import pydoc


def generate_api_docs(module_name: str, out_path: str) -> str:
    """Write plaintext API documentation for *module_name* to *out_path*."""
    doc = pydoc.render_doc(module_name, renderer=pydoc.plaintext)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(doc)
    return out_path
