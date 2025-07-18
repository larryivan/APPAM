#!/usr/bin/env python3
"""
测试ReAct修复 - 验证工具调用后能否继续生成响应
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app.services.ai_service import ai_service

def test_react_complete_flow():
    """测试完整的ReAct流程"""
    print("🧪 测试ReAct完整流程...")
    
    # 测试项目ID (确保这个项目存在)
    test_project_id = "fbda7827-37ff-4cd2-8416-413cb99536da"
    
    # 测试消息
    test_message = "请分析我的项目文件，告诉我有什么类型的文件"
    
    print(f"📝 测试消息: {test_message}")
    print(f"🗂️ 项目ID: {test_project_id}")
    print("\n🤖 AI响应流:")
    print("-" * 50)
    
    try:
        response_parts = []
        
        # 收集所有响应块
        for chunk in ai_service.get_react_response(test_message, test_project_id):
            print(chunk, end='', flush=True)
            response_parts.append(chunk)
        
        print("\n" + "-" * 50)
        
        # 分析响应
        full_response = ''.join(response_parts)
        
        print(f"\n📊 响应分析:")
        print(f"总字符数: {len(full_response)}")
        print(f"是否包含工具调用: {'🔧' in full_response}")
        print(f"是否包含工具结果: {'📊' in full_response}")
        print(f"是否包含最终分析: {'🎯' in full_response or ('分析' in full_response and len(full_response) > 500)}")
        
        # 检查是否完整
        if '🔧' in full_response and '📊' in full_response:
            if len(full_response) > 500 and ('分析' in full_response or '建议' in full_response):
                print("✅ ReAct流程完整：包含工具调用、结果和分析")
            else:
                print("⚠️ ReAct流程不完整：缺少最终分析")
        elif '🔧' in full_response:
            print("❌ ReAct流程中断：只有工具调用，没有最终分析")
        else:
            print("❌ ReAct流程失败：没有工具调用")
            
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_simple_tool_call():
    """测试简单的工具调用"""
    print("\n🔧 测试简单工具调用...")
    
    test_project_id = "fbda7827-37ff-4cd2-8416-413cb99536da"
    test_message = "列出项目文件"
    
    print(f"📝 测试消息: {test_message}")
    print(f"🗂️ 项目ID: {test_project_id}")
    print("\n🤖 AI响应:")
    print("-" * 30)
    
    try:
        for chunk in ai_service.get_react_response(test_message, test_project_id):
            print(chunk, end='', flush=True)
        print("\n" + "-" * 30)
        print("✅ 简单工具调用测试完成")
    except Exception as e:
        print(f"\n❌ 简单工具调用失败: {e}")

if __name__ == "__main__":
    print("🚀 开始测试ReAct修复...")
    
    # 检查AI服务配置
    print(f"ReAct启用状态: {ai_service.enable_react}")
    print(f"最大迭代次数: {ai_service.max_iterations}")
    print(f"模型: {ai_service.model}")
    
    # 运行测试
    test_simple_tool_call()
    test_react_complete_flow()
    
    print("\n✅ 所有测试完成!") 