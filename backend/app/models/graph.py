# app/models/graph.py
from enum import Enum
from pydantic import BaseModel
from typing import Optional

class NodeType(str, Enum):
    COMMIT = "Commit"
    FILE = "File"
    TEST = "Test"
    DEPENDENCY = "Dependency"
    PIPELINE_STEP = "PipelineStep"
    CONFIG_FILE = "ConfigFile"

class EdgeType(str, Enum):
    MODIFIES = "MODIFIES"
    INTRODUCES = "INTRODUCES"
    TESTS = "TESTS"
    DEPENDS_ON = "DEPENDS_ON"
    TRIGGERS = "TRIGGERS"
    FAILS_IN = "FAILS_IN"
    CONFIGURES = "CONFIGURES"

class GraphNode(BaseModel):
    id: str
    type: NodeType
    attributes: dict = {}

class GraphEdge(BaseModel):
    source: str
    target: str
    type: EdgeType
    attributes: dict = {}
