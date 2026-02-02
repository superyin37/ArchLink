"""
测试PDF预览功能 - 使用与下载功能相同的参数结构
"""
import requests
import os

# API基础URL
API_BASE_URL = "http://127.0.0.1:8002"

def test_pdf_preview():
    """测试PDF页面预览API"""
    
    # 测试参数 - 使用spec_code和page_code，与下载功能一致
    test_cases = [
        {"spec_code": "12J2", "page_code": "02", "page_number": 1, "dpi": 150},
        {"spec_code": "12J2", "page_code": "A10", "page_number": 1, "dpi": 150},
        {"spec_code": "15J401", "page_code": "5", "page_number": 1, "dpi": 150},
        {"spec_code": "15J401", "page_code": "A1", "page_number": 1, "dpi": 200},
    ]
    
    print("=" * 60)
    print("测试PDF预览功能")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        spec_code = test_case["spec_code"]
        page_code = test_case["page_code"]
        page_number = test_case.get("page_number", 1)
        dpi = test_case["dpi"]
        
        print(f"\n测试 {i}: 规范={spec_code}, 页码={page_code}, PDF内部页={page_number}, DPI={dpi}")
        print("-" * 60)
        
        try:
            # 发送请求
            url = f"{API_BASE_URL}/api/pdf-page-preview"
            params = {
                "spec_code": spec_code,
                "page_code": page_code,
                "page_number": page_number,
                "dpi": dpi
            }
            
            response = requests.get(url, params=params, timeout=30)
            
            # 检查响应
            if response.status_code == 200:
                # 检查是否是图片
                content_type = response.headers.get('Content-Type', '')
                if 'image' in content_type:
                    print(f"✓ 成功获取预览图片")
                    print(f"  - Content-Type: {content_type}")
                    print(f"  - 文件大小: {len(response.content) / 1024:.1f} KB")
                    
                    # 可选：保存图片到本地测试
                    output_file = f"test_preview_{spec_code}_{page_code}_p{page_number}.png"
                    with open(output_file, 'wb') as f:
                        f.write(response.content)
                    print(f"  - 已保存到: {output_file}")
                else:
                    print(f"✗ 响应不是图片格式: {content_type}")
                    print(f"  响应内容: {response.text[:200]}")
            else:
                print(f"✗ 请求失败: HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"  错误信息: {error_data.get('message', 'Unknown error')}")
                except:
                    print(f"  响应内容: {response.text[:200]}")
        
        except requests.exceptions.ConnectionError:
            print(f"✗ 连接失败: 无法连接到服务器 {API_BASE_URL}")
            print("  请确保服务器正在运行")
            break
        except Exception as e:
            print(f"✗ 异常: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_pdf_preview()
