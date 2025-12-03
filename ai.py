"""
AI 模块 - 使用 Google Gemini 分析灵感
"""

import google.generativeai as genai


class IdeaAnalyzer:
    """灵感分析器"""

    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")

    def analyze_idea(self, idea: str, available_models: list[str]) -> dict:
        """
        分析一条灵感，识别相关的思维模型

        Args:
            idea: 用户的灵感内容
            available_models: 可用的思维模型列表

        Returns:
            dict: {
                "matched_models": ["模型1", "模型2"],
                "tags": ["标签1", "标签2"],
                "analysis": "AI 分析内容"
            }
        """
        models_list = "\n".join([f"- {m}" for m in available_models])

        prompt = f"""你是一个思维模型专家。用户记录了一条灵感，请分析这条灵感：

## 用户的灵感
{idea}

## 可用的思维模型库
{models_list}

## 任务
1. 从上面的思维模型库中，找出与这条灵感最相关的 1-3 个思维模型（必须是列表中存在的）
2. 为这条灵感推荐 2-4 个标签（简短的关键词）
3. 写一段简短的分析（2-3句话），解释这条灵感体现了什么思维方式，以及可以如何深入思考

## 输出格式（严格按照此格式，方便解析）
MODELS: 模型1, 模型2
TAGS: 标签1, 标签2, 标签3
ANALYSIS: 你的分析内容

注意：
- MODELS 只能从上面的模型库中选择，不要编造
- 如果没有匹配的模型，MODELS 留空
- 保持分析简洁有深度"""

        try:
            response = self.model.generate_content(prompt)
            text = response.text

            # 解析响应
            result = {
                "matched_models": [],
                "tags": [],
                "analysis": "",
            }

            for line in text.strip().split("\n"):
                if line.startswith("MODELS:"):
                    models_str = line.replace("MODELS:", "").strip()
                    if models_str:
                        result["matched_models"] = [
                            m.strip() for m in models_str.split(",")
                            if m.strip() in available_models
                        ]
                elif line.startswith("TAGS:"):
                    tags_str = line.replace("TAGS:", "").strip()
                    if tags_str:
                        result["tags"] = [t.strip() for t in tags_str.split(",")]
                elif line.startswith("ANALYSIS:"):
                    result["analysis"] = line.replace("ANALYSIS:", "").strip()

            return result

        except Exception as e:
            print(f"AI 分析错误: {e}")
            return {
                "matched_models": [],
                "tags": [],
                "analysis": f"分析时出错: {str(e)}",
            }

    def generate_connection(self, idea1: str, idea2: str) -> str:
        """
        找出两条灵感之间的关联

        Args:
            idea1: 第一条灵感
            idea2: 第二条灵感

        Returns:
            关联分析
        """
        prompt = f"""你是一个善于发现联系的思考者。请找出下面两条灵感之间的潜在关联：

## 灵感 1
{idea1}

## 灵感 2
{idea2}

## 任务
1. 找出这两条灵感之间的潜在联系
2. 思考它们结合在一起能产生什么新的想法
3. 用 2-3 句话简洁地表达

请直接输出你的分析，不要有多余的格式。"""

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"分析时出错: {str(e)}"

    def generate_weekly_summary(self, ideas: list[dict], models_used: dict) -> str:
        """
        生成周报总结

        Args:
            ideas: 本周的灵感列表
            models_used: 使用的思维模型统计 {模型名: 次数}

        Returns:
            周报内容
        """
        ideas_text = "\n".join([f"- {i.get('preview', '')}" for i in ideas])
        models_text = "\n".join([f"- {k}: {v}次" for k, v in models_used.items()])

        prompt = f"""你是一个思维教练。请根据用户本周的灵感记录生成一份简短的周报。

## 本周灵感 ({len(ideas)} 条)
{ideas_text}

## 涉及的思维模型
{models_text if models_text else "暂无统计"}

## 任务
生成一份简短的周报，包括：
1. 本周思维活跃度评价（一句话）
2. 主要思考方向总结
3. 一个小建议或思考题

保持简洁，总共不超过 150 字。"""

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"生成周报时出错: {str(e)}"
