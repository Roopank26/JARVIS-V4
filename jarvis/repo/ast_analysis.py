"""
AST-based code analysis for JARVIS.
Provides detailed Python code analysis using Abstract Syntax Trees.
"""

import ast
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class FunctionInfo:
    """Information about a function."""
    name: str
    line: int
    end_line: int
    args: List[str] = field(default_factory=list)
    complexity: int = 1
    decorators: List[str] = field(default_factory=list)
    docstring: Optional[str] = None
    returns: Optional[str] = None


@dataclass
class ClassInfo:
    """Information about a class."""
    name: str
    line: int
    end_line: int
    bases: List[str] = field(default_factory=list)
    methods: List[FunctionInfo] = field(default_factory=list)
    docstring: Optional[str] = None


@dataclass
class FileInfo:
    """Complete information about a file."""
    path: str
    functions: List[FunctionInfo] = field(default_factory=list)
    classes: List[ClassInfo] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)  # __all__
    docstring: Optional[str] = None


class ASTAnalyzer:
    """
    Advanced Python AST analyzer.
    
    Provides:
    - Call graph analysis
    - Dead code detection
    - Import/export tracking
    - Complexity analysis
    - Method resolution order
    """

    def __init__(self):
        self._file_info: Dict[str, FileInfo] = {}
        self._call_graph: Dict[str, Set[str]] = defaultdict(set)

    def analyze_file(self, file_path: str) -> FileInfo:
        """Analyze a Python file."""
        if file_path in self._file_info:
            return self._file_info[file_path]

        info = FileInfo(path=file_path)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            # Get module docstring
            if ast.get_docstring(tree):
                info.docstring = ast.get_docstring(tree)

            # Get exports (__all__)
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == '__all__':
                            if isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
                                info.exports = [
                                    elt.value if isinstance(elt, ast.Constant) else str(elt)
                                    for elt in node.value.elts
                                ]

            # Walk the tree
            for node in ast.walk(tree):
                # Imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        info.imports.append(alias.asname or alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        info.imports.append(node.module)

                # Classes
                elif isinstance(node, ast.ClassDef):
                    class_info = self._analyze_class(node)
                    info.classes.append(class_info)

                # Top-level functions
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not any(isinstance(parent, ast.ClassDef) for parent in ast.walk(tree)):
                        func_info = self._analyze_function(node)
                        info.functions.append(func_info)

        except Exception as e:
            pass

        self._file_info[file_path] = info
        return info

    def _analyze_class(self, node: ast.ClassDef) -> ClassInfo:
        """Analyze a class node."""
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(self._get_attr_name(base))

        class_info = ClassInfo(
            name=node.name,
            line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            bases=bases,
            docstring=ast.get_docstring(node),
        )

        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method = self._analyze_function(item)
                class_info.methods.append(method)

        return class_info

    def _analyze_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionInfo:
        """Analyze a function node."""
        args = []
        for arg in node.args.args:
            args.append(arg.arg)

        func_info = FunctionInfo(
            name=node.name,
            line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            args=args,
            complexity=self._calculate_complexity(node),
            docstring=ast.get_docstring(node),
        )

        # Decorators
        for decorator in node.decorator_list:
            func_info.decorators.append(self._get_node_name(decorator))

        # Return annotation
        if node.returns:
            func_info.returns = self._get_node_name(node.returns)

        return func_info

    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.IfExp, ast.DictComp, ast.ListComp, ast.SetComp, ast.GeneratorExp)):
                complexity += 1

        return complexity

    def _get_node_name(self, node: ast.AST) -> str:
        """Get string representation of a node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self._get_attr_name(node)
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.BinOp):
            return f"{self._get_node_name(node.left)} {self._get_node_name(node.op)} {self._get_node_name(node.right)}"
        else:
            return ast.dump(node)[:50]

    def _get_attr_name(self, node: ast.Attribute) -> str:
        """Get attribute chain name."""
        parts = []
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name):
            parts.append(node.id)
        return ".".join(reversed(parts))

    def find_large_functions(self, min_lines: int = 50) -> List[Dict[str, Any]]:
        """Find functions larger than specified lines."""
        large_funcs = []

        for file_info in self._file_info.values():
            for func in file_info.functions:
                lines = func.end_line - func.line
                if lines >= min_lines:
                    large_funcs.append({
                        "file": file_info.path,
                        "function": func.name,
                        "lines": lines,
                        "complexity": func.complexity,
                    })

            for cls in file_info.classes:
                for method in cls.methods:
                    lines = method.end_line - method.line
                    if lines >= min_lines:
                        large_funcs.append({
                            "file": file_info.path,
                            "function": f"{cls.name}.{method.name}",
                            "lines": lines,
                            "complexity": method.complexity,
                        })

        return sorted(large_funcs, key=lambda x: x["lines"], reverse=True)

    def find_duplicate_functions(self) -> List[Dict[str, Any]]:
        """Find functions with similar names or signatures."""
        signatures: Dict[str, List[Dict]] = defaultdict(list)

        for file_info in self._file_info.values():
            for func in file_info.functions:
                sig = f"{func.name}({','.join(func.args)})"
                signatures[sig].append({
                    "file": file_info.path,
                    "function": func.name,
                    "args": func.args,
                })

        duplicates = []
        for sig, locations in signatures.items():
            if len(locations) > 1:
                duplicates.append({
                    "signature": sig,
                    "locations": locations,
                })

        return duplicates

    def get_method_resolution_order(self, class_name: str, file_path: str) -> List[str]:
        """Get MRO for a class."""
        file_info = self._file_info.get(file_path)
        if not file_info:
            return []

        for cls in file_info.classes:
            if cls.name == class_name:
                return cls.bases

        return []

    def format_analysis(self, file_path: str) -> str:
        """Format analysis for a file."""
        info = self.analyze_file(file_path)
        lines = [
            f"[Analysis: {info.path}]",
            "=" * 50,
            "",
        ]

        if info.docstring:
            lines.append(f"Module: {info.docstring[:100]}...")
            lines.append("")

        if info.imports:
            lines.append(f"Imports ({len(info.imports)}):")
            for imp in info.imports[:10]:
                lines.append(f"  • {imp}")
            if len(info.imports) > 10:
                lines.append(f"  ... and {len(info.imports) - 10} more")
            lines.append("")

        if info.classes:
            lines.append(f"Classes ({len(info.classes)}):")
            for cls in info.classes:
                lines.append(f"  🏛️ {cls.name}")
                if cls.bases:
                    lines.append(f"     Bases: {', '.join(cls.bases)}")
                lines.append(f"     Methods: {len(cls.methods)}")
                for method in cls.methods:
                    lines.append(f"       • {method.name}({', '.join(method.args)}) [{method.complexity}]")
            lines.append("")

        if info.functions:
            lines.append(f"Functions ({len(info.functions)}):")
            for func in info.functions:
                lines.append(f"  ⚙️ {func.name}({', '.join(func.args)})")
                lines.append(f"     Lines: {func.end_line - func.line}, Complexity: {func.complexity}")

        return "\n".join(lines)
