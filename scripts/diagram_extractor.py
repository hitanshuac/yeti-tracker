import ast
import os
from pathlib import Path


def get_imports(filepath):
    """Parse a python file and extract local imports."""
    with open(filepath, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=filepath)

    local_imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and (node.module.startswith("src.") or node.module == "app"):
                local_imports.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("src.") or alias.name == "app":
                    local_imports.add(alias.name)
    return local_imports


def scan_project():
    """Scan app.py and src/ for imports and generate D2 diagram."""
    base_dir = Path(__file__).parent.parent
    src_dir = base_dir / "src"

    modules = {}

    # Check app.py
    app_py = base_dir / "app.py"
    if app_py.exists():
        modules["app"] = get_imports(app_py)

    # Check src/*.py
    if src_dir.exists():
        for file in src_dir.glob("*.py"):
            if file.name != "__init__.py":
                mod_name = f"src.{file.stem}"
                modules[mod_name] = get_imports(file)

    return modules


def generate_d2(modules, output_path):
    """Format modules into a D2 string and write to file."""
    lines = [
        "direction: right",
        "classes: {",
        "  module: {",
        "    shape: rectangle",
        "    style: {",
        "      border-radius: 5",
        '      fill: "#1e1e1e"',
        '      stroke: "#ffffff"',
        '      font-color: "#ffffff"',
        "    }",
        "  }",
        "}",
        "",
    ]

    # Declare nodes
    for mod in modules.keys():
        lines.append(f"{mod.replace('.', '_')}: {mod} {{ class: module }}")

    lines.append("")

    # Declare edges
    for source, targets in modules.items():
        src_id = source.replace(".", "_")
        for target in targets:
            tgt_id = target.replace(".", "_")
            lines.append(f"{src_id} -> {tgt_id}")

    # Write output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[SUCCESS] Generated codebase architecture diagram at {output_path}")


if __name__ == "__main__":
    docs_dir = Path(__file__).parent.parent / "docs" / "assets"
    output_file = docs_dir / "auto_architecture.d2"

    deps = scan_project()
    generate_d2(deps, output_file)
