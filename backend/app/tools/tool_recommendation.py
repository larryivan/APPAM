"""
Tool recommendation system using LLM to analyze user queries and suggest relevant tools.
"""

import json
import os
from typing import Dict, List, Optional, Any
from openai import OpenAI, APITimeoutError, APIConnectionError
from .base import BaseTool, ToolResult


class ToolRecommendationTool(BaseTool):
    """Tool for providing intelligent tool recommendations based on user queries."""
    
    def __init__(self):
        super().__init__()
        self.client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url=os.getenv("DASHSCOPE_API_BASE"),
            timeout=60.0,  # 60 seconds timeout
            max_retries=2,  # Retry up to 2 times
        )
        self.model = os.getenv("DASHSCOPE_MODEL_NAME", "qwen-max")
        self.tool_library_path = os.path.join(os.path.dirname(__file__), '../../tool_library.json')
    
    @property
    def name(self) -> str:
        return "recommend_tools"
    
    @property
    def description(self) -> str:
        return "Analyze user query and recommend relevant bioinformatics tools from the tool library"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_query": {
                    "type": "string",
                    "description": "The user's question or request"
                },
                "project_id": {
                    "type": "string",
                    "description": "Current project ID (optional)"
                }
            },
            "required": ["user_query"]
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
    
    def _analyze_and_recommend(self, user_query: str, tools: List[Dict]) -> Optional[Dict]:
        """Use LLM to analyze user query and recommend relevant tools."""
        
        # Create a simplified tool list for the LLM
        tool_summaries = []
        for tool in tools:
            tool_summaries.append({
                "name": tool["tool_name"],
                "description": tool["description"]
            })
        
        system_prompt = """You are a bioinformatics expert assistant. Analyze the user's query and recommend the most relevant tool(s) from the provided tool library.

IMPORTANT: Only recommend tools when the user is explicitly asking for tool suggestions or needs help choosing tools. 

Your task:
1. Determine if the user is actually asking for tool recommendations
2. If yes, identify which tool(s) would be most helpful
3. If no, set has_recommendation to false

Response format (JSON):
{
  "has_recommendation": true/false,
  "recommended_tool": "tool_name" (if has_recommendation is true),
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation of why this tool is recommended",
  "alternative_tools": ["tool1", "tool2"] (optional, other potentially relevant tools)
}

Recommend tools ONLY when user asks:
- "What tool should I use for...?"
- "Which tool is best for...?"
- "Recommend a tool for..."
- "I need a tool to..."
- "Help me choose a tool for..."

Do NOT recommend tools for:
- General questions about how to perform tasks
- Theoretical or conceptual questions
- Data interpretation questions
- General bioinformatics knowledge

If no tool recommendation is appropriate, set has_recommendation to false.
Only recommend tools that are actually in the provided tool library.
Be concise but informative in your reasoning.
"""
        
        user_prompt = f"""User query: "{user_query}"

Available tools:
{json.dumps(tool_summaries, indent=2)}

Please analyze the query and provide your recommendation."""
        
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
            print(f"Network error in tool recommendation: {e}")
            return None
        except Exception as e:
            print(f"Error in tool recommendation LLM call: {e}")
            return None
        
        # Parse the LLM response
        response_text = response.choices[0].message.content.strip()
        
        # Try to extract JSON from the response
        try:
            # Look for JSON in the response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                recommendation = json.loads(json_match.group())
                return recommendation
            else:
                # Fallback: try to parse the entire response as JSON
                recommendation = json.loads(response_text)
                return recommendation
        except json.JSONDecodeError:
            print(f"Failed to parse LLM response as JSON: {response_text}")
            return None
        except Exception as e:
            print(f"Error in LLM analysis: {e}")
            return None
    
    def execute(self, user_query: str, project_id: Optional[str] = None) -> ToolResult:
        """Execute tool recommendation based on user query."""
        
        # Load tool library
        tools = self._load_tool_library()
        if not tools:
            return ToolResult(
                is_success=False,
                content="Failed to load tool library",
                metadata={"error": "Tool library not accessible"}
            )
        
        # Get LLM recommendation
        recommendation = self._analyze_and_recommend(user_query, tools)
        
        if not recommendation:
            return ToolResult(
                is_success=False,
                content="Failed to analyze query for tool recommendation",
                metadata={"error": "LLM analysis failed"}
            )
        
        # If no recommendation, return success but with no tool
        if not recommendation.get("has_recommendation", False):
            return ToolResult(
                is_success=True,
                content="No specific tool recommendation for this query",
                metadata={
                    "recommendation": None,
                    "query": user_query
                }
            )
        
        # Find the recommended tool details
        recommended_tool_name = recommendation.get("recommended_tool")
        recommended_tool_details = None
        
        for tool in tools:
            if tool["tool_name"].lower() == recommended_tool_name.lower():
                recommended_tool_details = tool
                break
        
        if not recommended_tool_details:
            return ToolResult(
                is_success=False,
                content=f"Recommended tool '{recommended_tool_name}' not found in tool library",
                metadata={"error": "Tool not found"}
            )
        
        # Prepare the result
        result_metadata = {
            "recommendation": {
                "tool_name": recommended_tool_details["tool_name"],
                "description": recommended_tool_details["description"],
                "confidence": recommendation.get("confidence", 0.8),
                "reasoning": recommendation.get("reasoning", ""),
                "alternative_tools": recommendation.get("alternative_tools", [])
            },
            "query": user_query,
            "project_id": project_id
        }
        
        return ToolResult(
            is_success=True,
            content=f"Recommended tool: {recommended_tool_details['tool_name']} - {recommendation.get('reasoning', '')}",
            metadata=result_metadata
        ) 