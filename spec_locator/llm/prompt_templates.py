"""
Prompt模板管理
"""


class PromptManager:
    """Prompt模板管理器"""
    
    # 系统提示词
    SYSTEM_PROMPT = """你是一个专业的建筑规范图纸识别专家，擅长从CAD截图中识别规范编号和页码。"""
    
    # 主识别Prompt（版本1）
    RECOGNITION_PROMPT_V1 = """
请仔细分析这张 CAD 截图，目标是 **精确提取**对应的 **规范编号（spec_code）** 与 **页码（page_code）**。注意图中可能包含尺寸标注、构造说明、材料说明等干扰信息，**不要将其误识别为页码或规范号**。

---

## 一、识别规范编号（spec_code）

规范编号常见示例：
`12J2`、`20G908-1`、`L13J5-1`、`23J908-8`、`参13J8` 等。

识别规律如下：

* 一般形式为：
  `(可选字母或汉字前缀) + 2~3位数字 + 1个字母 + 1~3位数字 + (可选“-后缀”)`
* 可能包含前缀字母（如 L）或汉字（如 参、苏 等），允许保留
* 可能包含短横线后缀（如 -1、-8）
* 优先选择最符合规范编号结构、且位于标注引线附近的文本作为 spec_code

---

## 二、识别页码（page_code）：必须结合版式结构判断

页码可能形如：
`C11`、`C11-2`、`P23`、`11`、`20` 等。

禁止仅凭文本外观判断页码，必须按照以下规则识别。

---

### 规则 A（最高优先级）：存在上下分割圆时

当在规范编号附近发现一个被水平线分割为上下两部分的圆形标注时：

* 必须使用该规则
* 页码一定在**下半圆区域**
* 上半圆通常为索引号或序号，不得作为页码
* page_code 必须取自下半圆内的文本

约束条件：

* 圆必须与规范号通过引线或空间位置明显关联
* 若下半圆存在多个候选文本，选择位置更居中、更清晰的那个
* 忽略圆外的所有数字

示例逻辑：
若规范号附近存在分割圆，上半为“1”，下半为“20”，则 page_code 必须为“20”。

---

### 规则 B：不存在分割圆时

当规范编号附近没有上下分割圆结构时，使用本规则。

特征：

* 规范号与页码通常位于同一行或同一注释块中
* 二者之间可能通过以下方式连接：

  * 空格
  * 短横线
  * 冒号
  * 斜杠
  * 组合符号

示例：
`12J2-C11-2`
`L13J5-1 11`
`20G908-1：P23`

提取方法：

1. 定位 spec_code 所在文本行或注释块
2. 在其右侧或后续紧邻位置查找页码候选
3. 优先选择：

   * 与 spec_code 距离最近
   * 且符合页码格式的文本
4. 排除明显属于尺寸、标高、编号序列的数字

---

## 三、优先级规则

1. 若检测到上下分割圆，必须使用规则 A
2. 仅当不存在该结构时，才允许使用规则 B
3. 不允许混合使用两种规则

---

## 四、输出格式（必须严格遵守）

请严格按照以下 JSON 格式输出：

```json
{
  "spec_code": "识别到的规范编号",
  "page_code": "识别到的页码",
  "confidence": 0.95,
  "reasoning": "说明：spec_code 的识别依据；使用了规则A还是规则B；若为规则A，明确说明页码来自下半圆；若为规则B，说明同一行/分隔关系及最近邻依据。"
}
```

---

## 五、无法可靠识别时的输出

当出现以下情况之一时，应判定为无法识别：

* 未找到明确的规范编号
* 存在分割圆但无法判断上下区域
* 页码候选过多且无法确定最近邻关系
* 结构严重模糊或被遮挡

请返回：

```json
{
  "spec_code": null,
  "page_code": null,
  "confidence": 0.0,
  "reasoning": "无法识别的具体原因说明"
}
```

"""
    
    @classmethod
    def get_prompt(cls, version: str = "v1") -> str:
        """
        获取指定版本的Prompt
        
        Args:
            version: Prompt版本号
            
        Returns:
            Prompt文本
        """
        if version == "v1":
            return cls.RECOGNITION_PROMPT_V1
        else:
            raise ValueError(f"Unknown prompt version: {version}")
    
    @classmethod
    def build_messages(cls, image_base64: str, version: str = "v1", provider: str = "doubao") -> list:
        """
        构建完整的消息列表（支持多种提供商格式）
        
        Args:
            image_base64: Base64编码的图片
            version: Prompt版本
            provider: LLM提供商 (doubao/openai/gemini)
            
        Returns:
            消息列表（根据不同提供商返回对应格式）
        """
        prompt_text = cls.get_prompt(version)
        
        if provider == "gemini":
            # Gemini格式：contents数组，parts包含text和inline_data
            return [{
                "parts": [
                    {"text": cls.SYSTEM_PROMPT + "\n\n" + prompt_text},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_base64
                        }
                    }
                ]
            }]
        
        elif provider in ["openai", "doubao"]:
            # OpenAI/豆包格式：messages数组，content可以是字符串或包含text+image_url的数组
            return [
                {
                    "role": "system",
                    "content": cls.SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt_text
                        }
                    ]
                }
            ]
        
        else:
            raise ValueError(f"Unknown provider: {provider}")
