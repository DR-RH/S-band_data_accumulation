import ast
from pathlib import Path


def create_test_structure(src_root: Path, test_root: Path) -> None:
    for py_file in src_root.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue

        relative = py_file.relative_to(src_root)
        test_file = test_root / relative.parent / f"test_{py_file.stem}.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)

        functions = extract_functions(py_file)

        content = generate_test_file_content(py_file, functions)

        if not test_file.exists():
            test_file.write_text(content)


def extract_functions(py_file: Path) -> list[str]:
    """
    Pythonファイルからトップレベル関数名を抽出
    """
    tree = ast.parse(py_file.read_text())

    functions = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            functions.append(node.name)

    return functions


def generate_test_file_content(src_file: Path, functions: list[str]) -> str:
    module_path = (
        src_file.with_suffix("")
        .as_posix()
        .replace("/", ".")
    )

    lines = []
    lines.append("import pytest")
    lines.append(f"from {module_path} import *\n")

    if not functions:
        lines.append("def test_placeholder():")
        lines.append("    assert True")
        return "\n".join(lines)

    for fn in functions:
        lines.append(f"\n\ndef test_{fn}():")
        lines.append(f"    # TODO: test {fn}")
        lines.append("    assert False")

    return "\n".join(lines)


if __name__ == "__main__":
    project_root = Path(".")

    src = project_root / "pipeline"
    tests = project_root / "tests" / "unit"

    create_test_structure(src, tests)

    print("Function-level test templates generated.")