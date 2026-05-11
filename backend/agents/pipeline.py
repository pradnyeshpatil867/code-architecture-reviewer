import json
from typing import TypedDict, Annotated
import operator

from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from langchain.schema import HumanMessage, SystemMessage

from models.schemas import ArchitectureIssue, GraphNode, GraphEdge


class AgentState(TypedDict):
    repo_url: str
    repo_info: dict
    tree_summary: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    language: str
    tech_stack: list[str]
    issues: Annotated[list[ArchitectureIssue], operator.add]
    summary: str
    metrics: dict
    ollama_model: str


def repo_analyzer_agent(state: AgentState) -> AgentState:
    llm = ChatOllama(model=state["ollama_model"], temperature=0)

    nodes_summary = "\n".join(
        f"- {n.label} ({n.type}): {n.file_count} files, "
        f"{n.metrics.get('lines', 0)} lines"
        for n in state["nodes"]
    )

    messages = [
        SystemMessage(content=(
            "You are an expert software architect. Analyze repository structure "
            "and identify the tech stack, architectural pattern, and project type. "
            "Respond ONLY with valid JSON — no markdown, no explanation."
        )),
        HumanMessage(content=f"""
Repository: {state['repo_url']}
Language: {state['language']}
Modules detected:
{nodes_summary}

Respond with this JSON:
{{
  "tech_stack": ["list", "of", "technologies"],
  "architectural_pattern": "e.g. MVC, microservices, monolith, layered",
  "project_type": "e.g. API server, full-stack app, CLI tool, library",
  "initial_observations": "2-3 sentence observation"
}}
"""),
    ]

    response = llm.invoke(messages)
    try:
        text = response.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text)
    except Exception:
        data = {
            "tech_stack": [state["language"]],
            "architectural_pattern": "unknown",
            "project_type": "unknown",
            "initial_observations": "Could not parse architecture details.",
        }

    state["tech_stack"] = data.get("tech_stack", [])
    state["metrics"]["architectural_pattern"] = data.get("architectural_pattern", "unknown")
    state["metrics"]["project_type"] = data.get("project_type", "unknown")
    state["metrics"]["initial_observations"] = data.get("initial_observations", "")
    return state


def dependency_mapper_agent(state: AgentState) -> AgentState:
    llm = ChatOllama(model=state["ollama_model"], temperature=0)

    edges_summary = "\n".join(
        f"- {e.source} → {e.target} ({e.label})"
        for e in state["edges"][:40]
    )

    high_coupling = [
        n for n in state["nodes"]
        if n.metrics.get("in_degree", 0) > 3
        or n.metrics.get("out_degree", 0) > 5
    ]
    coupling_summary = "\n".join(
        f"- {n.label}: {n.metrics.get('in_degree',0)} dependents, "
        f"{n.metrics.get('out_degree',0)} dependencies"
        for n in high_coupling
    )

    messages = [
        SystemMessage(content=(
            "You are a software architect specializing in dependency analysis. "
            "Identify architectural issues from dependency data. "
            "Respond ONLY with a valid JSON array — no markdown."
        )),
        HumanMessage(content=f"""
Dependency edges:
{edges_summary if edges_summary else "No cross-module dependencies detected."}

High-coupling modules:
{coupling_summary if coupling_summary else "None detected."}

Identify up to 4 issues. Respond with JSON array:
[
  {{
    "severity": "critical|warning|info",
    "title": "Short issue title",
    "description": "What the problem is",
    "affected_nodes": ["module1", "module2"],
    "suggestion": "How to fix it"
  }}
]
"""),
    ]

    response = llm.invoke(messages)
    issues = []
    try:
        text = response.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        for item in json.loads(text):
            issues.append(ArchitectureIssue(**item))
    except Exception:
        pass

    state["issues"] = issues
    return state


def architecture_critic_agent(state: AgentState) -> AgentState:
    llm = ChatOllama(model=state["ollama_model"], temperature=0.2)

    prior_issues = "\n".join(
        f"- [{i.severity.upper()}] {i.title}: {i.description}"
        for i in state["issues"]
    )

    messages = [
        SystemMessage(content=(
            "You are a senior software architect giving a concise, honest code review. "
            "Be specific, technical, and actionable. "
            "Respond ONLY with valid JSON — no markdown."
        )),
        HumanMessage(content=f"""
Repository: {state['repo_url']}
Pattern: {state['metrics'].get('architectural_pattern', 'unknown')}
Type: {state['metrics'].get('project_type', 'unknown')}
Tech stack: {', '.join(state['tech_stack'])}
Total modules: {len(state['nodes'])}
Total dependencies: {len(state['edges'])}

Issues found so far:
{prior_issues if prior_issues else "None"}

Respond with JSON:
{{
  "additional_issues": [
    {{
      "severity": "critical|warning|info",
      "title": "Issue title",
      "description": "Detailed description",
      "affected_nodes": ["module"],
      "suggestion": "Concrete fix"
    }}
  ],
  "executive_summary": "3-5 sentence architectural assessment"
}}
"""),
    ]

    response = llm.invoke(messages)
    try:
        text = response.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text)
        for item in data.get("additional_issues", []):
            state["issues"].append(ArchitectureIssue(**item))
        state["summary"] = data.get("executive_summary", "Analysis complete.")
    except Exception:
        state["summary"] = "Architecture analysis complete."

    return state


def build_agent_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("repo_analyzer", repo_analyzer_agent)
    workflow.add_node("dependency_mapper", dependency_mapper_agent)
    workflow.add_node("architecture_critic", architecture_critic_agent)
    workflow.set_entry_point("repo_analyzer")
    workflow.add_edge("repo_analyzer", "dependency_mapper")
    workflow.add_edge("dependency_mapper", "architecture_critic")
    workflow.add_edge("architecture_critic", END)
    return workflow.compile()


agent_graph = build_agent_graph()