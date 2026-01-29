"""
大模型识别模块测试脚本
快速验证LLM功能是否正常
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    """测试模块导入"""
    print("=" * 60)
    print("测试1: 检查模块导入")
    print("=" * 60)
    
    try:
        from spec_locator.llm import DoubaoEngine, PromptManager, ResponseParser
        print("✓ LLM模块导入成功")
        
        from spec_locator.config import LLMConfig
        print("✓ LLM配置导入成功")
        
        from spec_locator.core import SpecLocatorPipeline
        print("✓ Pipeline导入成功")
        
        return True
    except Exception as e:
        print(f"✗ 导入失败: {e}")
        return False


def test_config():
    """测试配置"""
    print("\n" + "=" * 60)
    print("测试2: 检查LLM配置")
    print("=" * 60)
    
    try:
        from spec_locator.config import LLMConfig
        
        print(f"LLM启用状态: {LLMConfig.ENABLED}")
        print(f"API密钥已配置: {'是' if LLMConfig.API_KEY else '否'}")
        print(f"模型: {LLMConfig.MODEL}")
        print(f"超时时间: {LLMConfig.TIMEOUT}秒")
        print(f"OCR置信度阈值: {LLMConfig.OCR_CONFIDENCE_THRESHOLD}")
        
        is_valid = LLMConfig.validate()
        if is_valid:
            print("✓ LLM配置有效")
        else:
            print("⚠ LLM配置不完整（可能缺少API密钥）")
        
        return True
    except Exception as e:
        print(f"✗ 配置检查失败: {e}")
        return False


def test_response_parser():
    """测试响应解析器"""
    print("\n" + "=" * 60)
    print("测试3: 测试响应解析器")
    print("=" * 60)
    
    try:
        from spec_locator.llm import ResponseParser
        
        # 测试标准JSON
        json_text = '{"spec_code": "12J2", "page_code": "C11", "confidence": 0.95}'
        result = ResponseParser.parse(json_text)
        assert result["spec_code"] == "12J2"
        print("✓ 标准JSON解析成功")
        
        # 测试Markdown格式
        markdown_text = """
这是结果：
```json
{
    "spec_code": "20G908-1",
    "page_code": "P23",
    "confidence": 0.88
}
```
"""
        result = ResponseParser.parse(markdown_text)
        assert result["spec_code"] == "20G908-1"
        print("✓ Markdown JSON解析成功")
        
        return True
    except Exception as e:
        print(f"✗ 解析器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_prompt_manager():
    """测试Prompt管理器"""
    print("\n" + "=" * 60)
    print("测试4: 测试Prompt管理器")
    print("=" * 60)
    
    try:
        from spec_locator.llm import PromptManager
        
        prompt = PromptManager.get_prompt("v1")
        assert "规范编号" in prompt
        assert "页码" in prompt
        print("✓ Prompt模板获取成功")
        
        messages = PromptManager.build_messages("dummy_base64", "v1")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        print("✓ 消息构建成功")
        
        return True
    except Exception as e:
        print(f"✗ Prompt管理器测试失败: {e}")
        return False


def test_pipeline_initialization():
    """测试Pipeline初始化"""
    print("\n" + "=" * 60)
    print("测试5: 测试Pipeline初始化")
    print("=" * 60)
    
    try:
        from spec_locator.core import SpecLocatorPipeline
        
        # 测试OCR模式
        pipeline_ocr = SpecLocatorPipeline(recognition_method="ocr")
        print("✓ OCR模式Pipeline初始化成功")
        
        # 测试Auto模式（不会真正初始化LLM，除非有API密钥）
        from spec_locator.config import LLMConfig
        if LLMConfig.API_KEY:
            pipeline_auto = SpecLocatorPipeline(recognition_method="auto")
            print("✓ Auto模式Pipeline初始化成功")
            
            if pipeline_auto.llm_engine:
                print("✓ LLM引擎已加载")
            else:
                print("⚠ LLM引擎未加载（可能缺少API密钥）")
        else:
            print("⚠ 跳过Auto模式测试（缺少API密钥）")
        
        return True
    except Exception as e:
        print(f"✗ Pipeline初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_endpoint():
    """测试API端点（需要服务运行）"""
    print("\n" + "=" * 60)
    print("测试6: 测试API端点")
    print("=" * 60)
    
    try:
        import requests
        
        # 测试健康检查
        response = requests.get("http://localhost:8002/health", timeout=3)
        data = response.json()
        
        print(f"服务状态: {data.get('status')}")
        print(f"OCR已加载: {data.get('ocr_loaded')}")
        print(f"LLM已启用: {data.get('llm_enabled')}")
        print(f"LLM已配置: {data.get('llm_configured')}")
        print("✓ API服务正常运行")
        
        return True
    except requests.exceptions.ConnectionError:
        print("⚠ API服务未运行（请先启动服务）")
        return False
    except Exception as e:
        print(f"✗ API测试失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("大模型识别模块测试")
    print("=" * 60)
    
    results = []
    
    # 运行测试
    results.append(("模块导入", test_imports()))
    results.append(("配置检查", test_config()))
    results.append(("响应解析器", test_response_parser()))
    results.append(("Prompt管理器", test_prompt_manager()))
    results.append(("Pipeline初始化", test_pipeline_initialization()))
    results.append(("API端点", test_api_endpoint()))
    
    # 输出总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name}: {status}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！大模型识别功能已就绪。")
    else:
        print("\n⚠ 部分测试未通过，请检查配置和依赖。")
    
    # 下一步提示
    print("\n" + "=" * 60)
    print("下一步操作")
    print("=" * 60)
    print("1. 配置API密钥:")
    print("   export DOUBAO_API_KEY=your_api_key_here")
    print("\n2. 启动服务:")
    print("   uvicorn spec_locator.api.server:app --host 0.0.0.0 --port 8002")
    print("\n3. 访问演示页面:")
    print("   file:///D:/projects/liuzong/spec_locator/api/demo.html")
    print("\n4. 查看文档:")
    print("   - 设计文档: LLM_INTEGRATION_DESIGN.md")
    print("   - 使用指南: LLM_README.md")
    print("   - API文档: LLM_API_DOCS.md")


if __name__ == "__main__":
    main()
