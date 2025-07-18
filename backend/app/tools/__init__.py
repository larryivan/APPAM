from .tool_registry import ToolRegistry
from .knowledge_tools import SearchKnowledgeBaseTool
from .system_tools import GetSystemInfoTool
from .project_tools import ListProjectFilesTool, ReadProjectFileTool, GetProjectStructureTool
from .tool_recommendation import ToolRecommendationTool
from .parameter_fill import ParameterFillTool
from .parameter_apply import ParameterApplyTool
from .smart_parameter_suggestion import SmartParameterSuggestionTool
from .bio_file_analyzer import BioFileAnalyzerTool

# List of all available tool classes
_all_tool_classes = [
    SearchKnowledgeBaseTool,
    GetSystemInfoTool,
    ListProjectFilesTool,
    ReadProjectFileTool,
    GetProjectStructureTool,
    ToolRecommendationTool,
    ParameterFillTool,
    ParameterApplyTool,
    SmartParameterSuggestionTool,
    BioFileAnalyzerTool,
]

# Instantiate all tool classes
_all_tools = [ToolClass() for ToolClass in _all_tool_classes]

# Create a global tool registry
tool_registry = ToolRegistry(tools=_all_tools)

def get_all_tools():
    """Returns a list of all tool instances."""
    return _all_tools

def get_tool_registry():
    """Returns the global tool registry instance."""
    return tool_registry

__all__ = ["tool_registry", "get_all_tools", "get_tool_registry"] 