"""
Smart Parameter Suggestion Tool

This tool uses LLM to intelligently analyze user queries and provide parameter suggestions
for bioinformatics tools when appropriate.
"""

import json
import os
from typing import Dict, List, Optional, Any
from openai import OpenAI, APITimeoutError, APIConnectionError
from .base import BaseTool, ToolResult
from ..services.knowledge_base import knowledge_base
from ..services.system_info import system_info_service
from ..services.file_manager import get_project_path, list_files


class SmartParameterSuggestionTool(BaseTool):
    """Tool for providing intelligent parameter suggestions based on user queries and tool context."""
    
    def __init__(self):
        super().__init__()
        self.client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url=os.getenv("DASHSCOPE_API_BASE"),
            timeout=60.0,
            max_retries=2,
        )
        self.model = os.getenv("DASHSCOPE_MODEL_NAME", "qwen-max")
        self.tool_library_path = os.path.join(os.path.dirname(__file__), '../../tool_library.json')
    
    @property
    def name(self) -> str:
        return "suggest_parameters"
    
    @property
    def description(self) -> str:
        return "Analyze user query and provide intelligent parameter suggestions for bioinformatics tools"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_message": {
                    "type": "string",
                    "description": "The user's message or query"
                },
                "tool_context": {
                    "type": "object",
                    "description": "Current tool context including tool name, parameters, and current values",
                    "properties": {
                        "tool_name": {"type": "string"},
                        "current_values": {"type": "object"},
                        "parameters": {"type": "array"}
                    }
                },
                "conversation_history": {
                    "type": "array",
                    "description": "Recent conversation history for context",
                    "items": {"type": "object"}
                },
                "project_id": {
                    "type": "string",
                    "description": "Current project ID"
                }
            },
            "required": ["user_message"]
        }
    
    def _load_tool_library(self) -> List[Dict]:
        """Load the tool library from JSON file."""
        try:
            with open(self.tool_library_path, 'r', encoding='utf-8') as f:
                tools = json.load(f)
            return tools
        except Exception as e:
            print(f"Error loading tool library: {e}")
            return []
    
    def _get_tool_definition(self, tool_name: str) -> Optional[Dict]:
        """Get tool definition from tool library."""
        tools = self._load_tool_library()
        for tool in tools:
            if tool["tool_name"].lower() == tool_name.lower():
                return tool
        return None
    
    def _should_exclude_parameter(self, param_name: str, param_info: Dict) -> bool:
        """Check if a parameter should be excluded from suggestions."""
        # Exclude input/output related parameters
        exclude_patterns = [
            "input", "output", "outdir", "out_dir", "input_files", 
            "input_dir", "input_reads", "reference_genome", "reference"
        ]
        
        param_name_lower = param_name.lower()
        
        # Check if parameter name contains excluded patterns
        for pattern in exclude_patterns:
            if pattern in param_name_lower:
                return True
        
        # Check if parameter type is file or directory (usually input/output)
        param_type = param_info.get("type", "").lower()
        if param_type in ["file", "directory"]:
            return True
        
        return False
    
    def _query_knowledge_base(self, tool_name: str, user_message: str) -> str:
        """Query knowledge base for relevant information about the tool and parameter configuration."""
        try:
            # Create search queries for different aspects
            search_queries = [
                f"{tool_name} parameter configuration best practices",
                f"{tool_name} optimization settings",
                f"how to configure {tool_name} parameters",
                f"{tool_name} 参数设置 配置"
            ]
            
            knowledge_content = []
            for query in search_queries:
                print(f"[PARAMETER SUGGESTION] Searching knowledge base: {query}")
                results = knowledge_base.search_knowledge(query, top_k=2)
                
                if results and len(results) > 0:
                    for result in results:
                        if result.get('score', 0) > 0.3:  # Only include relevant results
                            content = result.get('content', '')
                            if content and len(content) > 50:  # Only meaningful content
                                knowledge_content.append(content)
            
            if knowledge_content:
                combined_knowledge = "\n\n".join(knowledge_content[:3])  # Limit to top 3 results
                print(f"[PARAMETER SUGGESTION] Found {len(knowledge_content)} relevant knowledge entries")
                return combined_knowledge
            else:
                print(f"[PARAMETER SUGGESTION] No relevant knowledge found")
                return ""
                
        except Exception as e:
            print(f"[PARAMETER SUGGESTION] Knowledge base query error: {e}")
            return ""
    
    def _get_system_info(self) -> str:
        """Get current system information for parameter optimization."""
        try:
            print(f"[PARAMETER SUGGESTION] Getting system information")
            
            # Get system recommendations specifically for bioinformatics
            recommendations = system_info_service.get_bioinformatics_recommendations()
            
            if recommendations:
                system_info = f"CURRENT SYSTEM CONFIGURATION:\n"
                system_info += f"• CPU: {recommendations['threading']['max_threads']} cores (recommended: {recommendations['threading']['recommended_threads']})\n"
                system_info += f"• Memory: {recommendations['memory']['total_gb']} GB total, {recommendations['memory']['available_gb']} GB available\n"
                system_info += f"• Recommended max memory usage: {recommendations['memory']['recommended_max_memory_gb']} GB\n"
                system_info += f"• Available storage: {recommendations['storage']['available_space_gb']} GB\n"
                system_info += f"• System status: CPU load {recommendations['system_status']['cpu_load']:.1f}, Memory pressure {recommendations['system_status']['memory_pressure']}\n"
                
                return system_info
            else:
                return "System information not available"
                
        except Exception as e:
            print(f"[PARAMETER SUGGESTION] System info query error: {e}")
            return "System information not available"
    
    def _get_project_files_info(self, project_id: str) -> str:
        """Get information about files in the project directory."""
        try:
            if not project_id:
                return "No project specified"
            
            print(f"[PARAMETER SUGGESTION] Scanning project files for {project_id}")
            
            # Get basic project structure
            project_path = get_project_path(project_id)
            if not project_path or not os.path.exists(project_path):
                return "Project directory not found"
            
            # Scan for bioinformatics files
            bio_files = []
            
            def scan_directory(path: str, max_depth: int = 3, current_depth: int = 0):
                if current_depth > max_depth:
                    return
                
                try:
                    items = list_files(project_id, path)
                    if not items:
                        return
                    
                    for item in items:
                        if item['is_dir']:
                            # Recursively scan subdirectories
                            sub_path = os.path.join(path, item['name']).replace('\\', '/')
                            if sub_path.startswith('./'):
                                sub_path = sub_path[2:]
                            scan_directory(sub_path, max_depth, current_depth + 1)
                        else:
                            # Check for bioinformatics files
                            name = item['name'].lower()
                            if any(ext in name for ext in ['.fastq', '.fq', '.fasta', '.fa', '.vcf', '.sam', '.bam']):
                                bio_files.append({
                                    'name': item['name'],
                                    'path': os.path.join(path, item['name']).replace('\\', '/'),
                                    'size_mb': round(item['size'] / (1024 * 1024), 2),
                                    'type': self._detect_file_type(item['name'])
                                })
                                
                except Exception as e:
                    print(f"Error scanning directory {path}: {e}")
            
            scan_directory(".")
            
            # Generate files summary
            if bio_files:
                files_info = f"PROJECT FILES FOUND:\n"
                
                # Group by type
                by_type = {}
                for file in bio_files:
                    file_type = file['type']
                    if file_type not in by_type:
                        by_type[file_type] = []
                    by_type[file_type].append(file)
                
                for file_type, files in by_type.items():
                    files_info += f"• {file_type.upper()} files ({len(files)}): "
                    files_info += ", ".join([f"{f['name']} ({f['size_mb']}MB)" for f in files[:3]])
                    if len(files) > 3:
                        files_info += f" and {len(files) - 3} more"
                    files_info += "\n"
                
                total_size = sum(f['size_mb'] for f in bio_files)
                files_info += f"• Total data size: {total_size:.1f} MB\n"
                
                return files_info
            else:
                return "No bioinformatics files found in project"
                
        except Exception as e:
            print(f"[PARAMETER SUGGESTION] Project files scan error: {e}")
            return "Error scanning project files"
    
    def _detect_file_type(self, filename: str) -> str:
        """Detect file type from filename."""
        name = filename.lower()
        if '.fastq' in name or '.fq' in name:
            return 'fastq'
        elif '.fasta' in name or '.fa' in name or '.fas' in name or '.fna' in name:
            return 'fasta'
        elif '.vcf' in name:
            return 'vcf'
        elif '.sam' in name:
            return 'sam'
        elif '.bam' in name:
            return 'bam'
        else:
            return 'other'
    
    def _analyze_parameter_suggestion_need(self, user_message: str, tool_context: Dict) -> Dict:
        """Use LLM to analyze if parameter suggestions are needed and generate them."""
        
        if not tool_context or not tool_context.get("tool_name"):
            return {
                "needs_suggestion": False,
                "reason": "No tool context provided"
            }
        
        # Get tool definition
        tool_def = self._get_tool_definition(tool_context["tool_name"])
        if not tool_def:
            return {
                "needs_suggestion": False,
                "reason": "Tool definition not found"
            }
        
        # Filter parameters to exclude input/output related ones
        relevant_params = []
        for param in tool_def["parameters"]:
            if not self._should_exclude_parameter(param["name"], param):
                relevant_params.append(param)
        
        if not relevant_params:
            return {
                "needs_suggestion": False,
                "reason": "No relevant parameters to suggest"
            }
        
        # Get current values
        current_values = tool_context.get("current_values", {})
        
        # Get comprehensive context information
        print(f"[PARAMETER SUGGESTION] Gathering comprehensive context for {tool_context['tool_name']}")
        knowledge_content = self._query_knowledge_base(tool_context['tool_name'], user_message)
        system_info = self._get_system_info()
        project_files_info = self._get_project_files_info(tool_context.get('project_id', ''))
        
        # Prepare comprehensive system prompt
        system_prompt = f"""You are a bioinformatics expert assistant. Analyze the user's message to determine if they need parameter suggestions for the {tool_context['tool_name']} tool.

IMPORTANT RULES:
1. Only suggest parameters when the user is explicitly asking for help with tool configuration, parameter settings, or how to use the tool
2. Do NOT suggest parameters for general questions, explanations, or when the user is not asking for configuration help
3. Focus on parameters that need user input - exclude input/output files and directories
4. Only suggest parameters that are relevant to the user's specific use case
5. Use ALL available information below to provide intelligent, context-aware parameter recommendations

Tool: {tool_context['tool_name']}
Tool Description: {tool_def['description']}

Available parameters for suggestion:
{json.dumps(relevant_params, indent=2)}

Current parameter values:
{json.dumps(current_values, indent=2)}

KNOWLEDGE BASE INFORMATION:
{knowledge_content if knowledge_content else "No specific knowledge base information found for this tool."}

{system_info}

{project_files_info}

PARAMETER RECOMMENDATION GUIDELINES:
- Use system information to optimize thread counts and memory usage
- Consider project file sizes and types when suggesting parameters
- Base recommendations on bioinformatics best practices from knowledge base
- Provide specific values with clear explanations
- Consider current system load and available resources

Response format (JSON):
{{
  "needs_suggestion": true/false,
  "suggested_parameters": {{
    "param_name": {{
      "value": "suggested_value",
      "reasoning": "why this value is recommended"
    }}
  }},
  "summary": "Brief explanation of the suggestions"
}}

Only set needs_suggestion to true if the user is clearly asking for parameter configuration help.
"""
        
        user_prompt = f"""User message: "{user_message}"

Please analyze if the user needs parameter suggestions for the {tool_context['tool_name']} tool and provide appropriate recommendations."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
            else:
                return {
                    "needs_suggestion": False,
                    "reason": "Failed to parse LLM response"
                }
                
        except (APITimeoutError, APIConnectionError) as e:
            print(f"Network error in parameter suggestion: {e}")
            return {
                "needs_suggestion": False,
                "reason": f"Network error: {str(e)}"
            }
        except Exception as e:
            print(f"Error in parameter suggestion LLM call: {e}")
            return {
                "needs_suggestion": False,
                "reason": f"Error: {str(e)}"
            }
    
    def execute(self, **kwargs) -> ToolResult:
        """Execute the parameter suggestion analysis."""
        user_message = kwargs.get("user_message", "")
        tool_context = kwargs.get("tool_context", {})
        conversation_history = kwargs.get("conversation_history", [])
        project_id = kwargs.get("project_id", "")
        
        if not user_message.strip():
            return ToolResult(
                is_success=False,
                content="No user message provided"
            )
        
        # Add project_id to tool_context for comprehensive analysis
        if project_id:
            tool_context['project_id'] = project_id
        
        # Analyze if parameter suggestions are needed
        analysis_result = self._analyze_parameter_suggestion_need(user_message, tool_context)
        
        if not analysis_result.get("needs_suggestion", False):
            return ToolResult(
                is_success=False,
                content="No parameter suggestions needed",
                metadata={
                    "reason": analysis_result.get("reason", "User query does not require parameter suggestions")
                }
            )
        
        # Extract suggested parameters
        suggested_parameters = analysis_result.get("suggested_parameters", {})
        summary = analysis_result.get("summary", "Parameter suggestions generated")
        
        if not suggested_parameters:
            return ToolResult(
                is_success=False,
                content="No specific parameter suggestions generated"
            )
        
        return ToolResult(
            is_success=True,
            content=summary,
            metadata={
                "action": "parameter_suggestion",
                "tool_name": tool_context.get("tool_name"),
                "suggested_parameters": suggested_parameters,
                "summary": summary
            }
        ) 