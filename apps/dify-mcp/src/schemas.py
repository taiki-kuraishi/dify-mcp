"""
Dify Node Schemas

Re-exports Pydantic schemas from Dify entities for validation.
Based on: dify/api/core/workflow/nodes/*/entities.py
"""

# ruff: noqa: E402

import sys
from pathlib import Path

# Add Dify API to Python path
DIFY_API_PATH = Path(__file__).parent.parent.parent.parent / "dify" / "api"
if str(DIFY_API_PATH) not in sys.path:
    sys.path.insert(0, str(DIFY_API_PATH))

# Import entity classes from Dify
from core.workflow.nodes.llm.entities import (
    ContextConfig,
    LLMNodeData,
    ModelConfig,
    PromptConfig,
    VisionConfig,
)
from core.workflow.nodes.agent.entities import AgentNodeData
from core.workflow.nodes.answer.entities import AnswerNodeData
from core.workflow.nodes.code.entities import CodeNodeData
from core.workflow.nodes.datasource.entities import (
    DatasourceNodeData as DataSourceNodeData,
)
from core.workflow.nodes.document_extractor.entities import DocumentExtractorNodeData
from core.workflow.nodes.end.entities import EndNodeData
from core.workflow.nodes.http_request.entities import HttpRequestNodeData
from core.workflow.nodes.human_input.entities import HumanInputNodeData
from core.workflow.nodes.if_else.entities import IfElseNodeData
from core.workflow.nodes.iteration.entities import IterationNodeData
from core.workflow.nodes.knowledge_index.entities import KnowledgeIndexNodeData
from core.workflow.nodes.knowledge_retrieval.entities import KnowledgeRetrievalNodeData
from core.workflow.nodes.list_operator.entities import ListOperatorNodeData
from core.workflow.nodes.loop.entities import LoopNodeData
from core.workflow.nodes.parameter_extractor.entities import ParameterExtractorNodeData
from core.workflow.nodes.question_classifier.entities import QuestionClassifierNodeData
from core.workflow.nodes.start.entities import StartNodeData
from core.workflow.nodes.template_transform.entities import TemplateTransformNodeData
from core.workflow.nodes.tool.entities import ToolNodeData
from core.workflow.nodes.variable_aggregator.entities import (
    VariableAssignerNodeData as VariableAggregatorNodeData,
)
from core.plugin.entities.plugin import PluginDependency
from core.workflow.enums import NodeType

# Re-export for easy access
__all__ = [
    "AgentNodeData",
    "AnswerNodeData",
    "CodeNodeData",
    "ContextConfig",
    "DataSourceNodeData",
    "DocumentExtractorNodeData",
    "EndNodeData",
    "HttpRequestNodeData",
    "HumanInputNodeData",
    "IfElseNodeData",
    "IterationNodeData",
    "KnowledgeIndexNodeData",
    "KnowledgeRetrievalNodeData",
    "ListOperatorNodeData",
    "LLMNodeData",
    "LoopNodeData",
    "ModelConfig",
    "ParameterExtractorNodeData",
    "PromptConfig",
    "QuestionClassifierNodeData",
    "StartNodeData",
    "TemplateTransformNodeData",
    "ToolNodeData",
    "VariableAggregatorNodeData",
    "VisionConfig",
    "PluginDependency",
    "NodeType"
]

# Node type to schema mapping
# Maps node type strings (from DSL) to their corresponding Pydantic schema classes
NODE_SCHEMAS = {
    "agent": AgentNodeData,
    "answer": AnswerNodeData,
    "code": CodeNodeData,
    "datasource": DataSourceNodeData,
    "document-extractor": DocumentExtractorNodeData,
    "end": EndNodeData,
    "http-request": HttpRequestNodeData,
    "human-input": HumanInputNodeData,
    "if-else": IfElseNodeData,
    "iteration": IterationNodeData,
    "knowledge-index": KnowledgeIndexNodeData,
    "knowledge-retrieval": KnowledgeRetrievalNodeData,
    "list-operator": ListOperatorNodeData,
    "llm": LLMNodeData,
    "loop": LoopNodeData,
    "parameter-extractor": ParameterExtractorNodeData,
    "question-classifier": QuestionClassifierNodeData,
    "start": StartNodeData,
    "template-transform": TemplateTransformNodeData,
    "tool": ToolNodeData,
    "variable-aggregator": VariableAggregatorNodeData,
}
