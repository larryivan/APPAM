from typing import Dict, Any, Optional
import os
from .base import BaseTool, ToolResult
from ..services.file_manager import list_files, get_project_path, preview_file

class ListProjectFilesTool(BaseTool):
    """Tool to list files in a project directory."""

    @property
    def name(self) -> str:
        return "list_project_files"

    @property
    def description(self) -> str:
        return "Lists files and folders in a specified project directory, allowing for filtering by file type."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "The ID of the project."
                },
                "path": {
                    "type": "string",
                    "description": "The relative path within the project directory to list files from.",
                    "default": "."
                },
                "file_type": {
                    "type": "string",
                    "description": "Filter by file type (e.g., 'fastq', 'py').",
                    "default": ""
                }
            },
            "required": ["project_id"]
        }

    def execute(self, project_id: str, path: str = ".", file_type: str = "") -> ToolResult:
        """Executes the list files action."""
        try:
            items = list_files(project_id, path)
            
            if items is None:
                return ToolResult(is_success=False, content=f"Could not access project directory for project '{project_id}' at path '{path}'. It may not exist or permissions may be denied.")

            if file_type:
                file_type_lower = file_type.lower()
                items = [item for item in items if item and (file_type_lower in item.get('extension', '').lower() or file_type_lower in item.get('type', '').lower())]

            if not items:
                return ToolResult(is_success=True, content=f"No files found in directory '{path}'" + (f" of type '{file_type}'." if file_type else "."))

            folders = [item for item in items if item and item.get('is_dir', False)]
            files = [item for item in items if item and not item.get('is_dir', False)]
            
            result_str = f"Contents of '{path}' in project '{project_id}':\n\n"
            if folders:
                result_str += "📁 Folders:\n"
                for folder in folders:
                    result_str += f"  - {folder.get('name', 'unknown')}/\n"
                result_str += "\n"
            
            if files:
                result_str += "📄 Files:\n"
                for file in files:
                    size_mb = file.get('size', 0) / (1024 * 1024)
                    result_str += f"  - {file.get('name', 'unknown')} ({size_mb:.2f}MB, {file.get('type', 'file')})\n"

            return ToolResult(is_success=True, content=result_str)
        except Exception as e:
            return ToolResult(is_success=False, content=f"An error occurred while listing files: {e}", error_details=str(e))

class ReadProjectFileTool(BaseTool):
    """Tool to read the content of a file in a project."""

    @property
    def name(self) -> str:
        return "read_project_file"

    @property
    def description(self) -> str:
        return "Reads the content of a specified file within a project. Can preview large files or read the entire content."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "The ID of the project."
                },
                "file_path": {
                    "type": "string",
                    "description": "The relative path to the file within the project."
                },
                "preview_lines": {
                    "type": "integer",
                    "description": "Number of lines to preview. Set to 0 to read the entire file.",
                    "default": 100
                }
            },
            "required": ["project_id", "file_path"]
        }

    def execute(self, project_id: str, file_path: str, preview_lines: int = 100) -> ToolResult:
        """Executes the read file action."""
        try:
            if not file_path:
                return ToolResult(is_success=False, content="Error: File path was not specified.")

            if preview_lines > 0:
                result = preview_file(project_id, file_path, preview_lines)
                if result is None:
                    return ToolResult(is_success=False, content=f"Could not read file '{file_path}'. It may not exist or permissions are denied.")
                
                if result.get('too_large'):
                    return ToolResult(is_success=False, content=f"File '{file_path}' is too large to read fully in preview: {result.get('error')}")

                content = result.get('content', '') or ''
                return ToolResult(is_success=True, content=f"File: {file_path}\nType: {result.get('type', 'unknown')}\n\n{content}")
            else:
                # Full read
                abs_path = get_project_path(project_id, file_path)
                if not abs_path or not os.path.exists(abs_path):
                    return ToolResult(is_success=False, content=f"File not found: {file_path}")
                
                with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                return ToolResult(is_success=True, content=f"File: {file_path}\n\n{content}")

        except Exception as e:
            return ToolResult(is_success=False, content=f"An error occurred while reading file '{file_path}': {e}", error_details=str(e))

class GetProjectStructureTool(BaseTool):
    """Tool to get the directory structure of a project."""

    @property
    def name(self) -> str:
        return "get_project_structure"

    @property
    def description(self) -> str:
        return "Gets the complete directory structure of a project as a tree, which is useful for understanding the project layout."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "The ID of the project."
                },
                "max_depth": {
                    "type": "integer",
                    "description": "The maximum depth to traverse.",
                    "default": 3
                },
                "show_hidden": {
                    "type": "boolean",
                    "description": "Whether to show hidden files and folders.",
                    "default": False
                }
            },
            "required": ["project_id"]
        }

    def execute(self, project_id: str, max_depth: int = 3, show_hidden: bool = False) -> ToolResult:
        """Executes the get project structure action."""
        try:
            project_path = get_project_path(project_id)
            if not project_path or not os.path.exists(project_path):
                return ToolResult(is_success=False, content=f"Project with ID '{project_id}' not found.")

            tree_items = self._build_tree(project_path, max_depth=max_depth, show_hidden=show_hidden)
            if not tree_items:
                return ToolResult(is_success=True, content=f"Project directory '{project_id}' is empty or could not be read.")
            
            result_str = f"Project Structure ({project_id}):\n"
            result_str += f"{os.path.basename(project_path)}/\n"
            result_str += '\n'.join(tree_items)
            
            return ToolResult(is_success=True, content=result_str)
        except Exception as e:
            return ToolResult(is_success=False, content=f"An error occurred while getting project structure: {e}", error_details=str(e))

    def _build_tree(self, path: str, prefix: str = "", depth: int = 0, max_depth: int = 3, show_hidden: bool = False) -> list:
        if depth > max_depth:
            return []
            
        items = []
        try:
            entries = sorted(os.listdir(path))
            for i, entry in enumerate(entries):
                if not show_hidden and entry.startswith('.'):
                    continue
                
                entry_path = os.path.join(path, entry)
                is_last = i == (len(entries) - 1)
                
                if os.path.isdir(entry_path):
                    items.append(f"{prefix}{'└── ' if is_last else '├── '}{entry}/")
                    next_prefix = prefix + ("    " if is_last else "│   ")
                    items.extend(self._build_tree(entry_path, next_prefix, depth + 1, max_depth, show_hidden))
                else:
                    items.append(f"{prefix}{'└── ' if is_last else '├── '}{entry}")
        except PermissionError:
            items.append(f"{prefix}└── [Permission Denied]")
        
        return items

# I will add the other tools to this file in subsequent steps. 