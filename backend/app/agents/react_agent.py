import os
import json
from typing import Generator, List, Dict, Any, Optional
from openai import OpenAI, APITimeoutError, APIConnectionError
from ..tools import tool_registry

# Initialize OpenAI client with timeout settings
client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url=os.getenv("DASHSCOPE_API_BASE"),
    timeout=60.0,  # 60 seconds timeout
    max_retries=2,  # Retry up to 2 times
)

class ReActAgent:
    """A ReAct agent that uses an LLM to reason and act."""

    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations
        self.model = os.getenv("DASHSCOPE_MODEL_NAME", "qwen-max")
        self.system_prompt = self._get_default_system_prompt()
        self.last_tool_results = []  # Store tool execution results

    def run(self, user_message: str, project_id: Optional[str] = None, tool_context: Optional[Dict] = None) -> Generator[str, None, None]:
        """Runs the ReAct loop."""
        
        # Clear previous results
        self.last_tool_results = []
        
        # Build system prompt with tool context if available
        system_prompt = self.system_prompt
        if tool_context:
            print(f"[REACT AGENT] Tool context detected: {tool_context.get('tool_name', 'unknown')}")
            
            system_prompt += f"\n\n**Current Tool Context - PARAMETER CONFIGURATION MODE:**\n"
            system_prompt += f"User is currently on the {tool_context.get('tool_name', 'unknown')} tool page.\n"
            system_prompt += f"Tool description: {tool_context.get('description', 'No description')}\n"
            system_prompt += f"Available parameters: {', '.join(tool_context.get('parameters', []))}\n"
            system_prompt += f"Current parameter values: {tool_context.get('current_values', {})}\n\n"
            system_prompt += f"**IMPORTANT:** When user asks about parameter configuration, settings, or help:\n"
            system_prompt += f"1. IMMEDIATELY call `suggest_parameters` tool with the user's message\n"
            system_prompt += f"2. The tool will analyze the {tool_context.get('tool_name')} context and provide intelligent suggestions\n"
            system_prompt += f"3. After tool execution, summarize the suggestions and offer to apply them\n"
            system_prompt += f"4. DO NOT provide parameter advice without calling the tool first"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # Store tool recommendation for later use
        self.tool_recommendation = None
        
        # Inject project_id into tool arguments if available
        # This is a temporary solution until a more robust context management system is in place.
        if project_id:
            for tool in tool_registry.get_all_tools():
                if "project_id" in tool.parameters.get("properties", {}):
                    # This is a bit of a hack, we should find a better way to pass context
                    pass

        for i in range(self.max_iterations):
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tool_registry.get_tool_definitions(),
                    tool_choice="auto",
                )

                response_message = response.choices[0].message
                tool_calls = response_message.tool_calls

                if not tool_calls:
                    # No more tools to call, return the final response
                    if response_message.content:
                        yield response_message.content
                    return
            except (APITimeoutError, APIConnectionError) as e:
                error_msg = "抱歉，AI服务暂时无法连接，请稍后重试。"
                if "timeout" in str(e).lower():
                    error_msg = "AI服务响应超时，请检查网络连接后重试。"
                elif "connection" in str(e).lower():
                    error_msg = "无法连接到AI服务，请检查网络设置。"
                yield error_msg
                return
            except Exception as e:
                yield f"AI service error: {str(e)}"
                return

            messages.append(response_message)
            
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                arguments = tool_call.function.arguments
                
                # A simple way to inject project_id and tool_context if the tool needs it
                args_dict = json.loads(arguments)
                if project_id and "project_id" in tool_registry.get_tool(tool_name).parameters.get("properties", {}):
                    args_dict["project_id"] = project_id
                
                # Inject tool_context for parameter suggestion tool
                if tool_name == "suggest_parameters" and tool_context:
                    args_dict["tool_context"] = tool_context
                
                tool_result = tool_registry.execute_tool(tool_name, json.dumps(args_dict))
                
                # Store tool result for later access
                self.last_tool_results.append(tool_result)
                
                # Capture tool recommendation if this is the recommendation tool
                if tool_name == "recommend_tools" and tool_result.is_success and tool_result.metadata:
                    recommendation = tool_result.metadata.get("recommendation")
                    if recommendation:
                        self.tool_recommendation = recommendation
                
                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": tool_name,
                        "content": tool_result.content,
                    }
                )

        # Final response from the LLM after all tool calls
        try:
            final_response = client.chat.completions.create(
                model=self.model,
                messages=messages,
            )
            if final_response.choices[0].message.content:
                yield final_response.choices[0].message.content
        except (APITimeoutError, APIConnectionError) as e:
            error_msg = "抱歉，AI服务暂时无法连接，请稍后重试。"
            if "timeout" in str(e).lower():
                error_msg = "AI服务响应超时，请检查网络连接后重试。"
            elif "connection" in str(e).lower():
                error_msg = "无法连接到AI服务，请检查网络设置。"
            yield error_msg
        except Exception as e:
            yield f"AI service error: {str(e)}"

    def get_tool_recommendation(self) -> Optional[Dict]:
        """Get the tool recommendation from the last run."""
        return getattr(self, 'tool_recommendation', None)

    def _get_default_system_prompt(self) -> str:
        """Gets the default system prompt."""
        return """
You are a professional bioinformatics assistant with ReAct (Reasoning + Acting) capabilities.

**Core Principles:**
1. **Think, Act, Observe:** Follow the ReAct framework to solve problems. First, reason about the problem, then use a tool (act), observe the result, and repeat until you find the solution.
2. **Tool-First Approach:** Always prefer using a tool to get accurate, real-time information. Do not rely on assumptions or old knowledge.
3. **Analyze and Summarize:** After using a tool, you must provide a clear analysis or summary of the tool's output. Do not just state the raw result.
4. **Project-Awareness:** For tasks related to a specific project, use the project-related tools to gather context before providing answers. If you need a `project_id` and don't have one, ask the user for it.
5. **Clean Output:** Provide clean, formatted responses without debugging information or iteration markers. Focus on delivering clear, helpful content to the user.
6. **Selective Tool Recommendations:** Only use the `recommend_tools` function when users explicitly ask for tool suggestions or need help choosing tools. Do not automatically recommend tools for every bioinformatics question.

**Response Format:**
- Use proper markdown formatting for code blocks, lists, and emphasis
- Structure your responses with clear headings and sections
- Provide actionable insights and recommendations
- Avoid showing internal tool execution details to the user

**Tool Recommendation Guidelines:**
- ONLY use `recommend_tools` when users explicitly ask:
  - "What tool should I use for...?"
  - "Which tool is best for...?"
  - "Recommend a tool for..."
  - "I need a tool to..."
  - "Help me choose a tool for..."
- Do NOT use `recommend_tools` for general questions about:
  - How to perform tasks (explain the process instead)
  - Theoretical concepts or explanations
  - Data interpretation or analysis results
  - General bioinformatics knowledge
- When you do recommend tools, explain why they are relevant and mention alternatives when appropriate

**Parameter Configuration Guidelines - CRITICAL:**
- **ALWAYS** call `suggest_parameters` tool when users ask about parameter configuration:
  - "How should I set the parameters for [tool]?"
  - "What values should I use for [parameter]?"
  - "Help me configure [tool] for my data"
  - "I need help with [tool] parameters"
  - "参数配置", "参数设置", "配置建议"
  - "我需要你帮我设置参数"
  - Any question about tool parameter settings
- **NEVER** provide parameter suggestions without calling the tool first
- The `suggest_parameters` tool will:
  - Query the knowledge base for best practices
  - Analyze the current tool context and user needs
  - Generate intelligent parameter recommendations
  - Exclude input/output parameters automatically
  - Provide reasoning for each suggested value
- **When tool context is available:** Immediately recognize this as a parameter configuration scenario and call `suggest_parameters`
- **After tool execution:** Summarize the tool's output and offer to apply the suggested parameters
""" 