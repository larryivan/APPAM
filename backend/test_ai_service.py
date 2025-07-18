#!/usr/bin/env python3
"""
Test AI service ReAct functionality and project file access
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app.services.ai_service import ai_service

def test_tool_execution():
    """Test tool calling functionality"""
    print("🧪 Testing tool calling functionality...")
    
    # Test project ID
    test_project_id = "fbda7827-37ff-4cd2-8416-413cb99536da"
    
    # Test various tool calls
    test_cases = [
        # Test knowledge base search
        {
            "function_name": "search_knowledge_base",
            "args": {"query": "FastQ file quality control", "top_k": 3},
            "should_work": True
        },
        # Test system info
        {
            "function_name": "get_system_info",
            "args": {"info_type": "cpu"},
            "should_work": True
        },
        # Test list files (with project ID)
        {
            "function_name": "list_project_files",
            "args": {"path": ".", "file_type": ""},
            "should_work": True,
            "project_id": test_project_id
        },
        # Test list files (without project ID)
        {
            "function_name": "list_project_files",
            "args": {"path": ".", "file_type": ""},
            "should_work": False,
            "project_id": None
        },
        # Test read file
        {
            "function_name": "read_project_file",
            "args": {"file_path": "test_data.fastq", "preview_lines": 10},
            "should_work": True,
            "project_id": test_project_id
        },
        # Test project structure
        {
            "function_name": "get_project_structure",
            "args": {"max_depth": 2},
            "should_work": True,
            "project_id": test_project_id
        },
        # Test search files
        {
            "function_name": "search_in_files",
            "args": {"query": "ATCG", "file_pattern": "*.fastq"},
            "should_work": True,
            "project_id": test_project_id
        }
    ]
    
    # Create mock tool call object
    class MockToolCall:
        def __init__(self, function_name, args):
            self.function = MockFunction(function_name, args)
    
    class MockFunction:
        def __init__(self, name, args):
            self.name = name
            self.arguments = str(args).replace("'", '"')
    
    # Execute tests
    for i, test_case in enumerate(test_cases):
        print(f"\n📋 Test case {i+1}: {test_case['function_name']}")
        
        tool_call = MockToolCall(
            test_case["function_name"],
            test_case["args"]
        )
        
        project_id = test_case.get("project_id")
        result = ai_service._execute_tool_call(tool_call, project_id)
        
        print(f"Project ID: {project_id}")
        print(f"Expected success: {test_case['should_work']}")
        
        if test_case["should_work"]:
            if "错误" in result:
                print(f"❌ Failed: {result}")
            else:
                print(f"✅ Success: {result[:100]}...")
        else:
            if "错误" in result:
                print(f"✅ Correctly handled error: {result}")
            else:
                print(f"❌ Should have failed but succeeded: {result[:100]}...")

def test_react_response():
    """Test ReAct response"""
    print("\n🤖 Testing ReAct response...")
    
    test_project_id = "fbda7827-37ff-4cd2-8416-413cb99536da"
    test_message = "Please list my project files"
    
    print(f"Test message: {test_message}")
    print(f"Project ID: {test_project_id}")
    print("Response stream:")
    
    try:
        for chunk in ai_service.get_react_response(test_message, test_project_id):
            print(f"📤 {chunk}")
            if "错误" in chunk:
                break
    except Exception as e:
        print(f"❌ ReAct response failed: {e}")

if __name__ == "__main__":
    print("🚀 Starting AI service tests...")
    
    try:
        test_tool_execution()
        test_react_response()
        print("\n✅ All tests completed!")
    except Exception as e:
        print(f"\n❌ Tests failed: {e}")
        import traceback
        traceback.print_exc() 