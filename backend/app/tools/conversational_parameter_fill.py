"""
Conversational parameter fill tool for interactive parameter configuration.
"""

import json
import os
from typing import Dict, List, Optional, Any
from openai import OpenAI, APITimeoutError, APIConnectionError
from .base import BaseTool, ToolResult
from ..services import file_manager


class ConversationalParameterFillTool(BaseTool):
    """Tool for interactive parameter configuration through conversation."""
    
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
        return "conversational_parameter_fill"
    
    @property
    def description(self) -> str:
        return "Interactive parameter configuration through conversation"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tool_name": {
                    "type": "string",
                    "description": "Name of the tool that needs parameter configuration"
                },
                "tool_parameters": {
                    "type": "object",
                    "description": "Tool parameter schema with parameter definitions"
                },
                "current_values": {
                    "type": "object",
                    "description": "Current parameter values"
                },
                "user_message": {
                    "type": "string",
                    "description": "User's message or question about parameters"
                },
                "conversation_history": {
                    "type": "array",
                    "description": "Previous conversation history",
                    "items": {"type": "object"}
                },
                "project_id": {
                    "type": "string",
                    "description": "Current project ID for context"
                }
            },
            "required": ["tool_name", "tool_parameters", "user_message"]
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
            
            context = f"Project: {project_info.get('name', 'Unknown')}\n"
            context += f"Description: {project_info.get('description', 'No description')}\n\n"
            
            if files_result and files_result.get('files'):
                # Group files by type
                data_files = []
                result_files = []
                other_files = []
                
                for file_info in files_result['files']:
                    name = file_info['name']
                    if any(ext in name.lower() for ext in ['.fastq', '.fq', '.fasta', '.fa', '.vcf', '.sam', '.bam']):
                        data_files.append(file_info)
                    elif 'result' in name.lower() or 'output' in name.lower():
                        result_files.append(file_info)
                    else:
                        other_files.append(file_info)
                
                if data_files:
                    context += "Data files:\n"
                    for file_info in data_files[:10]:
                        context += f"  - {file_info['name']} ({file_info.get('size', 'Unknown size')})\n"
                
                if result_files:
                    context += "\nResult files:\n"
                    for file_info in result_files[:5]:
                        context += f"  - {file_info['name']}\n"
            
            return context
            
        except Exception as e:
            return f"Error getting project context: {str(e)}"
    
    def _conduct_conversation(self, tool_name: str, tool_parameters: Dict, current_values: Dict, 
                            user_message: str, conversation_history: List, project_context: str) -> Optional[Dict]:
        """Conduct conversational parameter configuration."""
        
        # Build conversation context
        conversation_context = ""
        if conversation_history:
            conversation_context = "\n\nPrevious conversation:\n"
            for msg in conversation_history[-5:]:  # Last 5 messages
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                conversation_context += f"{role}: {content}\n"
        
        system_prompt = f"""You are a bioinformatics expert assistant helping users configure parameters for the {tool_name} tool.

Your role is to:
1. Understand the user's question or request about parameters
2. Provide helpful explanations and suggestions
3. Ask clarifying questions when needed
4. Guide the user through parameter configuration step by step
5. Suggest specific parameter values based on their data and goals

Tool Information:
- Tool: {tool_name}
- Available parameters: {list(tool_parameters.keys())}

Project Context:
{project_context}

Current Parameter Values:
{json.dumps(current_values, indent=2)}

Parameter Definitions:
{json.dumps(tool_parameters, indent=2)}

Response Guidelines:
- Be conversational and helpful
- Ask one question at a time
- Provide specific, actionable suggestions
- Explain why certain parameters are recommended
- If suggesting parameter values, format them clearly
- Focus on performance and analysis parameters, avoid input/output file paths
- Only suggest parameters that are truly necessary or beneficial
- Don't feel obligated to fill all parameters - some can be left as defaults

Response Format (JSON):
{{
  "message": "Your conversational response to the user",
  "parameter_suggestions": {{
    "parameter_name": {{
      "value": "suggested_value",
      "reasoning": "Why this value is recommended"
    }}
  }},
  "questions": ["Any follow-up questions you have"],
  "next_steps": ["What the user should consider next"],
  "ready_to_apply": false
}}

Set "ready_to_apply" to true only if you have enough information to provide complete parameter configuration.
"""
        
        user_prompt = f"User message: {user_message}{conversation_context}"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
        except (APITimeoutError, APIConnectionError) as e:
            print(f"Network error in conversational parameter fill: {e}")
            return None
        except Exception as e:
            print(f"Error in conversational parameter fill LLM call: {e}")
            return None
        
        # Parse the LLM response
        response_text = response.choices[0].message.content.strip()
        
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
            else:
                # Fallback: try to parse entire response as JSON
                result = json.loads(response_text)
                return result
        except json.JSONDecodeError:
            # If JSON parsing fails, create a simple response
            return {
                "message": response_text,
                "parameter_suggestions": {},
                "questions": [],
                "next_steps": [],
                "ready_to_apply": False
            }
        except Exception as e:
            print(f"Error parsing conversational response: {e}")
            return None
    
    def execute(self, tool_name: str, tool_parameters: Dict, user_message: str,
                current_values: Optional[Dict] = None, conversation_history: Optional[List] = None,
                project_id: Optional[str] = None) -> ToolResult:
        """Execute conversational parameter configuration."""
        
        current_values = current_values or {}
        conversation_history = conversation_history or []
        
        # Get project context
        project_context = self._get_project_context(project_id)
        
        # Conduct conversation
        result = self._conduct_conversation(
            tool_name, 
            tool_parameters, 
            current_values,
            user_message,
            conversation_history,
            project_context
        )
        
        if not result:
            return ToolResult(
                is_success=False,
                content="Failed to process conversational parameter configuration",
                metadata={"error": "LLM conversation failed"}
            )
        
        # Prepare result metadata
        result_metadata = {
            "tool_name": tool_name,
            "message": result.get("message", ""),
            "parameter_suggestions": result.get("parameter_suggestions", {}),
            "questions": result.get("questions", []),
            "next_steps": result.get("next_steps", []),
            "ready_to_apply": result.get("ready_to_apply", False),
            "project_id": project_id,
            "conversation_type": "parameter_configuration"
        }
        
        # Create response content
        content = result.get("message", "I'm here to help you configure the parameters.")
        
        return ToolResult(
            is_success=True,
            content=content,
            metadata=result_metadata
        ) 