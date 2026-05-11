from pydantic import BaseModel
from typing import Optional


class AnalysisRequest(BaseModel):
    repo_url: str
    github_token: Optional[str] = None
    ollama_model: str = "llama3"


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    file_count: int
    issues: list[str]
    metrics: dict


class GraphEdge(BaseModel):
    source: str
    target: str
    weight: int
    label: str


class ArchitectureIssue(BaseModel):
    severity: str
    title: str
    description: str
    affected_nodes: list[str]
    suggestion: str


class AnalysisResponse(BaseModel):
    repo_name: str
    language: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    issues: list[ArchitectureIssue]
    summary: str
    tech_stack: list[str]
    metrics: dict