from typing import Dict, Any
from .base import BaseTool, ToolResult
from ..services.knowledge_base import knowledge_base

class SearchKnowledgeBaseTool(BaseTool):
    """Tool to search the knowledge base."""

    @property
    def name(self) -> str:
        return "search_knowledge_base"

    @property
    def description(self) -> str:
        return "Searches the bioinformatics knowledge base for relevant information and guidance."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to find relevant information in the knowledge base."
                },
                "top_k": {
                    "type": "integer",
                    "description": "The number of top results to return.",
                    "default": 3
                }
            },
            "required": ["query"]
        }

    def execute(self, query: str, top_k: int = 3) -> ToolResult:
        """Executes the knowledge base search."""
        try:
            results = knowledge_base.search_knowledge(query, top_k)

            if results is None:
                return ToolResult(
                    is_success=False,
                    content="Knowledge base search service is currently unavailable. Please try again later."
                )

            if not results:
                return ToolResult(is_success=True, content="No relevant content found in the knowledge base.")

            # Filter results with low similarity
            # Using a threshold from the original implementation for consistency
            knowledge_similarity_threshold = 0.5
            filtered_results = [r for r in results if r and r.get('similarity', 0) >= knowledge_similarity_threshold]

            if not filtered_results:
                return ToolResult(is_success=True, content="No sufficiently relevant content found in the knowledge base.")

            # Format the search results
            search_result_str = f"Knowledge Base Search Results (Query: {query}):\n\n"
            for i, result in enumerate(filtered_results, 1):
                metadata = result.get('metadata', {}) or {}
                content = result.get('content', '') or ''
                similarity = result.get('similarity', 0)

                search_result_str += f"{i}. Source: {metadata.get('filename', 'Unknown Document')}\n"
                search_result_str += f"   Similarity: {similarity:.2f}\n"
                search_result_str += f"   Content: {content[:600]}...\n\n"

            return ToolResult(is_success=True, content=search_result_str)

        except Exception as e:
            return ToolResult(
                is_success=False,
                content=f"An error occurred while searching the knowledge base: {e}",
                error_details=str(e)
            ) 