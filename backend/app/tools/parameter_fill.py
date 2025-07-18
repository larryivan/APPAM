"""
Parameter fill tool for intelligent parameter suggestion based on context and project files.
"""

import json
import os
from typing import Dict, List, Optional, Any
from openai import OpenAI, APITimeoutError, APIConnectionError
from .base import BaseTool, ToolResult
from ..services import file_manager


class ParameterFillTool(BaseTool):
    """Tool for providing intelligent parameter filling suggestions."""
    
    def __init__(self):
        super().__init__()
        self.client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url=os.getenv("DASHSCOPE_API_BASE"),
            timeout=60.0,
            max_retries=2,
        )
        self.model = os.getenv("DASHSCOPE_MODEL_NAME", "qwen-max")
    
    @property
    def name(self) -> str:
        return "fill_parameters"
    
    @property
    def description(self) -> str:
        return "Analyze tool parameters and provide intelligent filling suggestions based on project context"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tool_name": {
                    "type": "string",
                    "description": "Name of the tool that needs parameter filling"
                },
                "tool_parameters": {
                    "type": "object",
                    "description": "Tool parameter schema with parameter definitions"
                },
                "project_id": {
                    "type": "string",
                    "description": "Current project ID for context"
                },
                "user_context": {
                    "type": "string",
                    "description": "Additional context from user about their goals"
                }
            },
            "required": ["tool_name", "tool_parameters"]
        }
    
    def _get_project_context(self, project_id: Optional[str]) -> str:
        """Get project context including file listings and structure."""
        if not project_id:
            return "No project context available."
        
        try:
            # Get project info
            project_info = file_manager.get_project_by_id(project_id)
            if not project_info:
                return "Could not access project information."
            
            # Get list of files in project
            files_result = file_manager.list_files(project_id, '')
            
            context = f"Project ID: {project_id}\n"
            context += f"Project Name: {project_info.get('name', 'Unknown')}\n"
            context += f"Project Description: {project_info.get('description', 'No description')}\n\n"
            
            if files_result and files_result.get('files'):
                context += "Available files:\n"
                for file_info in files_result['files'][:20]:  # Limit to first 20 files
                    context += f"- {file_info['name']} ({file_info.get('size', 'Unknown size')})\n"
            
            return context
            
        except Exception as e:
            return f"Error getting project context: {str(e)}"
    
    def _analyze_parameters(self, tool_name: str, tool_parameters: Dict, project_context: str, user_context: str) -> Optional[Dict]:
        """Use LLM to analyze parameters and generate suggestions."""
        
        system_prompt = """You are a bioinformatics expert assistant specializing in parameter configuration for analysis tools.

Your task is to analyze the tool parameters and provide intelligent suggestions based on:
1. The tool's purpose and typical usage patterns
2. Available project files and data
3. User's stated goals and context
4. Best practices for the specific tool

Response format (JSON):
{
  "suggestions": {
    "parameter_name": {
      "value": "suggested_value",
      "reasoning": "Why this value is recommended",
      "confidence": 0.0-1.0,
      "alternatives": ["alternative1", "alternative2"]
    }
  },
  "summary": "Brief summary of the parameter suggestions",
  "warnings": ["Any potential issues or things to consider"],
  "missing_info": ["Information that would help improve suggestions"]
}

Guidelines:
- Only suggest parameters that are provided in the tool_parameters schema
- Use project files as input/output paths when appropriate
- Consider file formats, sizes, and naming patterns
- Provide practical, working values
- Explain your reasoning clearly
- Be conservative with confidence scores
- Suggest reasonable defaults for optional parameters
"""
        
        user_prompt = f"""Tool: {tool_name}

Tool Parameters Schema:
{json.dumps(tool_parameters, indent=2)}

Project Context:
{project_context}

User Context: {user_context if user_context else "No specific context provided"}

Please analyze these parameters and provide intelligent suggestions."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2  # Lower temperature for more consistent parameter suggestions
            )
        except (APITimeoutError, APIConnectionError) as e:
            print(f"Network error in parameter fill: {e}")
            return None
        except Exception as e:
            print(f"Error in parameter fill LLM call: {e}")
            return None
        
        # Parse the LLM response
        response_text = response.choices[0].message.content.strip()
        
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                suggestions = json.loads(json_match.group())
                return suggestions
            else:
                # Fallback: try to parse entire response as JSON
                suggestions = json.loads(response_text)
                return suggestions
        except json.JSONDecodeError:
            print(f"Failed to parse parameter suggestions as JSON: {response_text}")
            return None
        except Exception as e:
            print(f"Error parsing parameter suggestions: {e}")
            return None
    
    def execute(self, tool_name: str, tool_parameters: Dict, project_id: Optional[str] = None, user_context: Optional[str] = None) -> ToolResult:
        """Execute parameter filling analysis."""
        
        # Get project context
        project_context = self._get_project_context(project_id)
        
        # Analyze parameters with LLM
        suggestions = self._analyze_parameters(
            tool_name, 
            tool_parameters, 
            project_context, 
            user_context or ""
        )
        
        if not suggestions:
            return ToolResult(
                is_success=False,
                content="Failed to generate parameter suggestions",
                metadata={"error": "LLM analysis failed"}
            )
        
        # Prepare result
        result_metadata = {
            "tool_name": tool_name,
            "suggestions": suggestions.get("suggestions", {}),
            "summary": suggestions.get("summary", ""),
            "warnings": suggestions.get("warnings", []),
            "missing_info": suggestions.get("missing_info", []),
            "project_id": project_id
        }
        
        # Create summary content
        summary = f"Parameter suggestions for {tool_name}:\n\n"
        summary += suggestions.get("summary", "Generated parameter recommendations.")
        
        if suggestions.get("warnings"):
            summary += f"\n\n⚠️ Warnings:\n"
            for warning in suggestions["warnings"]:
                summary += f"- {warning}\n"
        
        return ToolResult(
            is_success=True,
            content=summary,
            metadata=result_metadata
        ) 