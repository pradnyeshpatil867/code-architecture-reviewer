import re
import networkx as nx
from collections import defaultdict
from models.schemas import GraphNode, GraphEdge


CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx",
    ".go", ".java", ".rb", ".rs", ".cpp", ".c",
}

IGNORE_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv",
    "venv", "dist", "build", ".next", "coverage",
}

IMPORT_PATTERNS = {
    "python": [
        re.compile(r"^from\s+([\w.]+)\s+import", re.MULTILINE),
        re.compile(r"^import\s+([\w.]+)", re.MULTILINE),
    ],
    "javascript": [
        re.compile(r'(?:import|require)\s*[\(\s]["\']([^"\']+)["\']', re.MULTILINE),
        re.compile(r'from\s+["\']([^"\']+)["\']', re.MULTILINE),
    ],
}


def classify_node_type(path: str) -> str:
    p = path.lower()
    if any(x in p for x in ["test", "spec", "__test__"]):
        return "test"
    if any(x in p for x in ["config", "setting", ".env", "conf"]):
        return "config"
    if any(x in p for x in ["util", "helper", "common", "shared"]):
        return "utility"
    if any(x in p for x in ["service", "provider", "client", "api"]):
        return "service"
    if any(x in p for x in ["model", "schema", "entity", "type"]):
        return "model"
    if any(x in p for x in ["router", "route", "controller", "view", "page"]):
        return "router"
    return "module"


def get_top_dir(path: str) -> str:
    parts = path.split("/")
    return parts[0] if len(parts) > 1 else "__root__"


def extract_imports(content: str, language: str) -> list[str]:
    patterns = IMPORT_PATTERNS.get(language, IMPORT_PATTERNS["javascript"])
    found = []
    for pat in patterns:
        found.extend(pat.findall(content))
    return found


def detect_language(files: list[dict]) -> str:
    ext_count: dict[str, int] = defaultdict(int)
    for f in files:
        path = f.get("path", "")
        ext = "." + path.rsplit(".", 1)[-1] if "." in path else ""
        ext_count[ext] += 1
    if ext_count.get(".py", 0) > ext_count.get(".js", 0):
        return "python"
    return "javascript"


def build_graph(
    tree: list[dict],
    file_contents: dict[str, str],
) -> tuple[nx.DiGraph, list[GraphNode], list[GraphEdge]]:
    G = nx.DiGraph()

    code_files = [
        f for f in tree
        if f.get("type") == "blob"
        and any(f["path"].endswith(ext) for ext in CODE_EXTENSIONS)
        and not any(d in f["path"].split("/") for d in IGNORE_DIRS)
    ]

    language = detect_language(code_files)

    dir_files: dict[str, list[str]] = defaultdict(list)
    for f in code_files:
        top = get_top_dir(f["path"])
        dir_files[top].append(f["path"])

    node_data: dict[str, dict] = {}
    for top_dir, files in dir_files.items():
        all_imports: list[str] = []
        total_lines = 0
        for fp in files:
            content = file_contents.get(fp, "")
            total_lines += content.count("\n")
            all_imports.extend(extract_imports(content, language))

        node_data[top_dir] = {
            "files": files,
            "imports": all_imports,
            "lines": total_lines,
            "type": classify_node_type(top_dir),
        }
        G.add_node(top_dir, **node_data[top_dir])

    edge_weights: dict[tuple, int] = defaultdict(int)
    for src_dir, data in node_data.items():
        for imp in data["imports"]:
            for tgt_dir in node_data:
                if tgt_dir == src_dir:
                    continue
                if tgt_dir.lower() in imp.lower() or \
                   imp.replace(".", "/").startswith(tgt_dir):
                    edge_weights[(src_dir, tgt_dir)] += 1

    for (src, tgt), weight in edge_weights.items():
        G.add_edge(src, tgt, weight=weight)

    issues_per_node: dict[str, list[str]] = defaultdict(list)

    for node in G.nodes:
        in_deg = G.in_degree(node)
        out_deg = G.out_degree(node)
        if in_deg > 5:
            issues_per_node[node].append(
                f"High coupling: {in_deg} modules depend on this"
            )
        if out_deg > 8:
            issues_per_node[node].append(
                f"Too many dependencies: imports from {out_deg} modules"
            )

    try:
        cycles = list(nx.simple_cycles(G))
        for cycle in cycles[:5]:
            for node in cycle:
                issues_per_node[node].append(
                    f"Circular dependency: {' → '.join(cycle)}"
                )
    except Exception:
        pass

    schema_nodes = []
    for node_id, data in node_data.items():
        schema_nodes.append(GraphNode(
            id=node_id,
            label=node_id,
            type=data["type"],
            file_count=len(data["files"]),
            issues=issues_per_node[node_id],
            metrics={
                "lines": data["lines"],
                "in_degree": G.in_degree(node_id),
                "out_degree": G.out_degree(node_id),
                "imports_count": len(data["imports"]),
            },
        ))

    schema_edges = []
    for (src, tgt), weight in edge_weights.items():
        schema_edges.append(GraphEdge(
            source=src,
            target=tgt,
            weight=weight,
            label=f"{weight} import{'s' if weight > 1 else ''}",
        ))

    return G, schema_nodes, schema_edges