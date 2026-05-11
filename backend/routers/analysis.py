import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from models.schemas import AnalysisRequest, AnalysisResponse
from services.github_service import GitHubService
from services.graph_builder import (
    build_graph, detect_language, CODE_EXTENSIONS, IGNORE_DIRS
)
from agents.pipeline import agent_graph

router = APIRouter()


async def stream_analysis(request: AnalysisRequest):
    async def send(event: str, data: dict):
        yield f"event: {event}\ndata: {json.dumps(data)}\n\n"

    try:
        async for chunk in send("progress", {"step": 1, "message": "Connecting to GitHub..."}):
            yield chunk

        github = GitHubService(token=request.github_token)
        owner, repo = github.parse_repo(request.repo_url)
        repo_info = await github.get_repo_info(owner, repo)
        languages = await github.get_languages(owner, repo)
        primary_lang = max(languages, key=languages.get) if languages else "Unknown"

        async for chunk in send("progress", {"step": 2, "message": f"Fetching file tree for {owner}/{repo}..."}):
            yield chunk

        tree = await github.get_tree(owner, repo)

        code_files = [
            f for f in tree
            if f.get("type") == "blob"
            and any(f["path"].endswith(ext) for ext in CODE_EXTENSIONS)
            and not any(d in f["path"].split("/") for d in IGNORE_DIRS)
        ][:60]

        async for chunk in send("progress", {"step": 3, "message": f"Reading {len(code_files)} source files..."}):
            yield chunk

        file_contents: dict[str, str] = {}
        for i in range(0, len(code_files), 10):
            batch = code_files[i:i + 10]
            results = await asyncio.gather(
                *[github.get_file_content(owner, repo, f["path"]) for f in batch],
                return_exceptions=True,
            )
            for f, content in zip(batch, results):
                if isinstance(content, str):
                    file_contents[f["path"]] = content

        async for chunk in send("progress", {"step": 4, "message": "Building dependency graph..."}):
            yield chunk

        language = detect_language(code_files)
        _, nodes, edges = build_graph(tree, file_contents)

        if not nodes:
            async for chunk in send("error", {"message": "No analyzable source files found."}):
                yield chunk
            return

        async for chunk in send("progress", {"step": 5, "message": "Running AI agents (~30s)..."}):
            yield chunk

        initial_state = {
            "repo_url": request.repo_url,
            "repo_info": repo_info,
            "tree_summary": f"{len(tree)} files total",
            "nodes": nodes,
            "edges": edges,
            "language": language,
            "tech_stack": [],
            "issues": [],
            "summary": "",
            "metrics": {
                "total_files": len(tree),
                "code_files": len(code_files),
                "primary_language": primary_lang,
                "stars": repo_info.get("stargazers_count", 0),
                "forks": repo_info.get("forks_count", 0),
            },
            "ollama_model": request.ollama_model,
        }

        final_state = agent_graph.invoke(initial_state)

        async for chunk in send("progress", {"step": 6, "message": "Finalizing results..."}):
            yield chunk

        result = AnalysisResponse(
            repo_name=f"{owner}/{repo}",
            language=primary_lang,
            nodes=final_state["nodes"],
            edges=final_state["edges"],
            issues=final_state["issues"],
            summary=final_state["summary"],
            tech_stack=final_state["tech_stack"],
            metrics=final_state["metrics"],
        )

        async for chunk in send("result", result.model_dump()):
            yield chunk

    except ValueError as e:
        async for chunk in send("error", {"message": str(e)}):
            yield chunk
    except Exception as e:
        async for chunk in send("error", {"message": f"Analysis failed: {str(e)}"}):
            yield chunk


@router.post("/analyze")
async def analyze(request: AnalysisRequest):
    return StreamingResponse(
        stream_analysis(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )