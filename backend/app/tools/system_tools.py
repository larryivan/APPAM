from typing import Dict, Any, Literal
from .base import BaseTool, ToolResult
from ..services.system_info import system_info_service

class GetSystemInfoTool(BaseTool):
    """Tool to get system information."""

    @property
    def name(self) -> str:
        return "get_system_info"

    @property
    def description(self) -> str:
        return (
            "Retrieves real-time system information, including CPU, memory, disk usage, "
            "and bioinformatics analysis performance recommendations."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "info_type": {
                    "type": "string",
                    "description": "The type of system information to retrieve.",
                    "enum": ["cpu", "memory", "disk", "load", "recommendations", "status", "full"],
                    "default": "recommendations"
                }
            },
            "required": []
        }

    def execute(self, info_type: Literal["cpu", "memory", "disk", "load", "recommendations", "status", "full"] = "recommendations") -> ToolResult:
        """Executes the system info retrieval."""
        try:
            result_str = self._get_info_as_string(info_type)
            if "无法获取" in result_str or "出错" in result_str:
                 return ToolResult(is_success=False, content=result_str)
            return ToolResult(is_success=True, content=result_str)
        except Exception as e:
            return ToolResult(
                is_success=False,
                content=f"An error occurred while fetching system info: {e}",
                error_details=str(e)
            )

    def _get_info_as_string(self, info_type: str) -> str:
        """Helper to get formatted string for different info types."""
        if info_type == "cpu":
            data = system_info_service.get_cpu_info()
            if data is None:
                return "无法获取CPU信息，系统服务暂时不可用"
            
            result = "CPU Info:\n"
            result += f"- Physical Cores: {data.get('physical_cores', 'N/A')}\n"
            result += f"- Logical Cores: {data.get('logical_cores', 'N/A')}\n"
            result += f"- CPU Usage: {data.get('usage_percent', 0):.1f}%\n"
            result += f"- Architecture: {data.get('architecture', 'N/A')}\n"
            return result

        if info_type == "memory":
            data = system_info_service.get_memory_info()
            if data is None:
                return "无法获取内存信息，系统服务暂时不可用"
            
            result = "Memory Info:\n"
            result += f"- Total Memory: {data.get('total', 0) / (1024**3):.1f} GB\n"
            result += f"- Available Memory: {data.get('available', 0) / (1024**3):.1f} GB\n"
            result += f"- Used Memory: {data.get('used', 0) / (1024**3):.1f} GB\n"
            result += f"- Usage Percent: {data.get('usage_percent', 0):.1f}%\n"
            return result

        # ... other info_types can be added here following the same pattern ...
        
        # Fallback for other types from the original implementation
        if info_type == "recommendations":
            recommendations = system_info_service.get_bioinformatics_recommendations()
            if recommendations is None:
                return "无法获取生物信息学分析建议，系统服务暂时不可用"
            return f"Bioinformatics Analysis Recommendations:\n{recommendations}"

        return "Error: Invalid information type" 