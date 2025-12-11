"""
AI 模块 - 支持多种 AI 后端（Gemini、OpenAI、Claude）
"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseAnalyzer(ABC):
    """AI 分析器基类"""

    @abstractmethod
    def analyze_idea(self, idea: str, available_models: list[str]) -> dict:
        """分析灵感"""
        pass

    @abstractmethod
    def generate_connection(self, idea1: str, idea2: str) -> str:
        """分析两条灵感的关联"""
        pass

    @abstractmethod
    def generate_weekly_summary(self, ideas: list[dict], models_used: dict) -> str:
        """生成周报"""
        pass

    @abstractmethod
    def search_mental_model(self, keyword: str) -> Optional[dict]:
        """搜索思维模型"""
        pass

    @abstractmethod
    def analyze_image(self, image_data: bytes, mime_type: str) -> str:
        """分析图片"""
        pass

    @abstractmethod
    def transcribe_audio(self, audio_data: bytes, mime_type: str) -> str:
        """语音转文字"""
        pass

    def _get_analyze_idea_prompt(self, idea: str, models_list: str) -> str:
        """获取灵感分析的 prompt"""
        return f"""你是一个思维模型专家。用户记录了一条灵感，请分析这条灵感：

## 用户的灵感
{idea}

## 可用的思维模型库
{models_list}

## 任务
1. 从上面的思维模型库中，找出与这条灵感最相关的 1-3 个思维模型（必须是列表中存在的）
2. 为这条灵感推荐 2-4 个标签（简短的关键词）
3. 写一段简短的分析（2-3句话），解释这条灵感体现了什么思维方式，以及可以如何深入思考
4. 如果现有模型库中没有很匹配的模型，推荐一个新的思维模型（从你的知识库中找一个真实存在的、广为人知的思维模型）

## 输出格式（严格按照此格式，方便解析）
MODELS: 模型1, 模型2
TAGS: 标签1, 标签2, 标签3
ANALYSIS: 你的分析内容
NEW_MODEL: 模型名称|模型简介（如果不需要推荐新模型，则留空）

注意：
- MODELS 只能从上面的模型库中选择，不要编造
- 如果没有匹配的模型，MODELS 留空
- NEW_MODEL 只在现有库匹配度不高时才推荐，推荐真实存在的思维模型
- 保持分析简洁有深度"""

    def _get_connection_prompt(self, idea1: str, idea2: str) -> str:
        """获取关联分析的 prompt"""
        return f"""你是一个善于发现联系的思考者。请找出下面两条灵感之间的潜在关联：

## 灵感 1
{idea1}

## 灵感 2
{idea2}

## 任务
1. 找出这两条灵感之间的潜在联系
2. 思考它们结合在一起能产生什么新的想法
3. 用 2-3 句话简洁地表达

请直接输出你的分析，不要有多余的格式。"""

    def _get_weekly_summary_prompt(self, ideas: list[dict], models_used: dict) -> str:
        """获取周报的 prompt"""
        ideas_text = "\n".join([f"- {i.get('preview', '')}" for i in ideas])
        models_text = "\n".join([f"- {k}: {v}次" for k, v in models_used.items()])

        return f"""你是一个思维教练。请根据用户本周的灵感记录生成一份简短的周报。

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

    def _get_search_model_prompt(self, keyword: str) -> str:
        """获取搜索模型的 prompt"""
        return f"""你是一个思维模型专家。请根据关键词搜索并介绍一个相关的思维模型。

## 搜索关键词
{keyword}

## 任务
找到一个与关键词相关的、真实存在的、广为人知的思维模型，并详细介绍。

## 输出格式（严格按照此格式）
NAME: 思维模型名称
DEFINITION: 一句话定义
KEY_POINTS: 要点1; 要点2; 要点3
APPLICATIONS: 应用场景1; 应用场景2; 应用场景3
REPRESENTATIVES: 代表人物或来源（如有）

注意：
- 只推荐真实存在的思维模型，不要编造
- 如果找不到匹配的模型，NAME 填「未找到」"""

    def _get_image_prompt(self) -> str:
        """获取图片分析的 prompt"""
        return """请分析这张图片：
1. 如果图片中有文字，请提取所有文字内容
2. 如果是图表、笔记、思维导图等，请描述其主要内容和结构
3. 如果是其他类型的图片，请简要描述图片内容

直接输出提取或描述的内容，不要有多余的格式。"""

    def _get_audio_prompt(self) -> str:
        """获取语音转文字的 prompt"""
        return "请将这段语音转录为文字，直接输出转录内容，不要有多余的格式。"

    def _parse_idea_analysis(self, text: str, available_models: list[str]) -> dict:
        """解析灵感分析结果"""
        result = {
            "matched_models": [],
            "tags": [],
            "analysis": "",
            "suggested_new_model": None,
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
            elif line.startswith("NEW_MODEL:"):
                new_model_str = line.replace("NEW_MODEL:", "").strip()
                if new_model_str and "|" in new_model_str:
                    parts = new_model_str.split("|", 1)
                    result["suggested_new_model"] = {
                        "name": parts[0].strip(),
                        "description": parts[1].strip() if len(parts) > 1 else "",
                    }

        return result

    def _parse_model_search(self, text: str) -> Optional[dict]:
        """解析模型搜索结果"""
        result = {
            "name": "",
            "definition": "",
            "key_points": [],
            "applications": [],
            "representatives": "",
        }

        for line in text.strip().split("\n"):
            if line.startswith("NAME:"):
                result["name"] = line.replace("NAME:", "").strip()
            elif line.startswith("DEFINITION:"):
                result["definition"] = line.replace("DEFINITION:", "").strip()
            elif line.startswith("KEY_POINTS:"):
                points_str = line.replace("KEY_POINTS:", "").strip()
                result["key_points"] = [p.strip() for p in points_str.split(";") if p.strip()]
            elif line.startswith("APPLICATIONS:"):
                apps_str = line.replace("APPLICATIONS:", "").strip()
                result["applications"] = [a.strip() for a in apps_str.split(";") if a.strip()]
            elif line.startswith("REPRESENTATIVES:"):
                result["representatives"] = line.replace("REPRESENTATIVES:", "").strip()

        if result["name"] and result["name"] != "未找到":
            return result
        return None


class GeminiAnalyzer(BaseAnalyzer):
    """Google Gemini 分析器"""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.model_name = model

    def analyze_idea(self, idea: str, available_models: list[str]) -> dict:
        models_list = "\n".join([f"- {m}" for m in available_models])
        prompt = self._get_analyze_idea_prompt(idea, models_list)

        try:
            response = self.model.generate_content(prompt)
            return self._parse_idea_analysis(response.text, available_models)
        except Exception as e:
            print(f"AI 分析错误: {e}")
            return {
                "matched_models": [],
                "tags": [],
                "analysis": f"分析时出错: {str(e)}",
                "suggested_new_model": None,
            }

    def generate_connection(self, idea1: str, idea2: str) -> str:
        prompt = self._get_connection_prompt(idea1, idea2)
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"分析时出错: {str(e)}"

    def generate_weekly_summary(self, ideas: list[dict], models_used: dict) -> str:
        prompt = self._get_weekly_summary_prompt(ideas, models_used)
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"生成周报时出错: {str(e)}"

    def search_mental_model(self, keyword: str) -> Optional[dict]:
        prompt = self._get_search_model_prompt(keyword)
        try:
            response = self.model.generate_content(prompt)
            return self._parse_model_search(response.text)
        except Exception as e:
            print(f"搜索思维模型出错: {e}")
            return None

    def analyze_image(self, image_data: bytes, mime_type: str = "image/jpeg") -> str:
        prompt = self._get_image_prompt()
        try:
            response = self.model.generate_content([
                prompt,
                {"mime_type": mime_type, "data": image_data}
            ])
            return response.text.strip()
        except Exception as e:
            return f"图片分析出错: {str(e)}"

    def transcribe_audio(self, audio_data: bytes, mime_type: str = "audio/ogg") -> str:
        prompt = self._get_audio_prompt()
        try:
            response = self.model.generate_content([
                prompt,
                {"mime_type": mime_type, "data": audio_data}
            ])
            return response.text.strip()
        except Exception as e:
            return f"语音转录出错: {str(e)}"


class OpenAIAnalyzer(BaseAnalyzer):
    """OpenAI 分析器"""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model_name = model

    def _chat(self, prompt: str) -> str:
        """发送聊天请求"""
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    def analyze_idea(self, idea: str, available_models: list[str]) -> dict:
        models_list = "\n".join([f"- {m}" for m in available_models])
        prompt = self._get_analyze_idea_prompt(idea, models_list)

        try:
            text = self._chat(prompt)
            return self._parse_idea_analysis(text, available_models)
        except Exception as e:
            print(f"AI 分析错误: {e}")
            return {
                "matched_models": [],
                "tags": [],
                "analysis": f"分析时出错: {str(e)}",
                "suggested_new_model": None,
            }

    def generate_connection(self, idea1: str, idea2: str) -> str:
        prompt = self._get_connection_prompt(idea1, idea2)
        try:
            return self._chat(prompt).strip()
        except Exception as e:
            return f"分析时出错: {str(e)}"

    def generate_weekly_summary(self, ideas: list[dict], models_used: dict) -> str:
        prompt = self._get_weekly_summary_prompt(ideas, models_used)
        try:
            return self._chat(prompt).strip()
        except Exception as e:
            return f"生成周报时出错: {str(e)}"

    def search_mental_model(self, keyword: str) -> Optional[dict]:
        prompt = self._get_search_model_prompt(keyword)
        try:
            text = self._chat(prompt)
            return self._parse_model_search(text)
        except Exception as e:
            print(f"搜索思维模型出错: {e}")
            return None

    def analyze_image(self, image_data: bytes, mime_type: str = "image/jpeg") -> str:
        import base64
        prompt = self._get_image_prompt()
        base64_image = base64.b64encode(image_data).decode("utf-8")

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}
                    ]
                }]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"图片分析出错: {str(e)}"

    def transcribe_audio(self, audio_data: bytes, mime_type: str = "audio/ogg") -> str:
        """使用 Whisper API 转录"""
        import tempfile
        import os

        # 根据 mime_type 确定文件扩展名
        ext_map = {"audio/ogg": ".ogg", "audio/mp3": ".mp3", "audio/wav": ".wav", "audio/m4a": ".m4a"}
        ext = ext_map.get(mime_type, ".ogg")

        try:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
                f.write(audio_data)
                temp_path = f.name

            with open(temp_path, "rb") as audio_file:
                response = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )

            os.unlink(temp_path)
            return response.text.strip()
        except Exception as e:
            return f"语音转录出错: {str(e)}"


class GrokAnalyzer(BaseAnalyzer):
    """xAI Grok 分析器（OpenAI 兼容接口）"""

    def __init__(self, api_key: str, model: str = "grok-2-latest"):
        from openai import OpenAI
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1"
        )
        self.model_name = model

    def _chat(self, prompt: str) -> str:
        """发送聊天请求"""
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    def analyze_idea(self, idea: str, available_models: list[str]) -> dict:
        models_list = "\n".join([f"- {m}" for m in available_models])
        prompt = self._get_analyze_idea_prompt(idea, models_list)

        try:
            text = self._chat(prompt)
            return self._parse_idea_analysis(text, available_models)
        except Exception as e:
            print(f"AI 分析错误: {e}")
            return {
                "matched_models": [],
                "tags": [],
                "analysis": f"分析时出错: {str(e)}",
                "suggested_new_model": None,
            }

    def generate_connection(self, idea1: str, idea2: str) -> str:
        prompt = self._get_connection_prompt(idea1, idea2)
        try:
            return self._chat(prompt).strip()
        except Exception as e:
            return f"分析时出错: {str(e)}"

    def generate_weekly_summary(self, ideas: list[dict], models_used: dict) -> str:
        prompt = self._get_weekly_summary_prompt(ideas, models_used)
        try:
            return self._chat(prompt).strip()
        except Exception as e:
            return f"生成周报时出错: {str(e)}"

    def search_mental_model(self, keyword: str) -> Optional[dict]:
        prompt = self._get_search_model_prompt(keyword)
        try:
            text = self._chat(prompt)
            return self._parse_model_search(text)
        except Exception as e:
            print(f"搜索思维模型出错: {e}")
            return None

    def analyze_image(self, image_data: bytes, mime_type: str = "image/jpeg") -> str:
        import base64
        prompt = self._get_image_prompt()
        base64_image = base64.b64encode(image_data).decode("utf-8")

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}
                    ]
                }]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"图片分析出错: {str(e)}"

    def transcribe_audio(self, audio_data: bytes, mime_type: str = "audio/ogg") -> str:
        return "语音转录出错: Grok 暂不支持语音转录，请使用 Gemini 或 OpenAI"


class LocalAnalyzer(BaseAnalyzer):
    """本地模型分析器（Ollama、LM Studio 等 OpenAI 兼容接口）"""

    def __init__(self, api_key: str, model: str = "qwen2.5:7b", base_url: str = "http://localhost:11434/v1"):
        from openai import OpenAI
        self.client = OpenAI(
            api_key=api_key or "not-needed",  # 本地模型通常不需要 key
            base_url=base_url
        )
        self.model_name = model
        self.base_url = base_url

    def _chat(self, prompt: str) -> str:
        """发送聊天请求"""
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    def analyze_idea(self, idea: str, available_models: list[str]) -> dict:
        models_list = "\n".join([f"- {m}" for m in available_models])
        prompt = self._get_analyze_idea_prompt(idea, models_list)

        try:
            text = self._chat(prompt)
            return self._parse_idea_analysis(text, available_models)
        except Exception as e:
            print(f"AI 分析错误: {e}")
            return {
                "matched_models": [],
                "tags": [],
                "analysis": f"分析时出错: {str(e)}",
                "suggested_new_model": None,
            }

    def generate_connection(self, idea1: str, idea2: str) -> str:
        prompt = self._get_connection_prompt(idea1, idea2)
        try:
            return self._chat(prompt).strip()
        except Exception as e:
            return f"分析时出错: {str(e)}"

    def generate_weekly_summary(self, ideas: list[dict], models_used: dict) -> str:
        prompt = self._get_weekly_summary_prompt(ideas, models_used)
        try:
            return self._chat(prompt).strip()
        except Exception as e:
            return f"生成周报时出错: {str(e)}"

    def search_mental_model(self, keyword: str) -> Optional[dict]:
        prompt = self._get_search_model_prompt(keyword)
        try:
            text = self._chat(prompt)
            return self._parse_model_search(text)
        except Exception as e:
            print(f"搜索思维模型出错: {e}")
            return None

    def analyze_image(self, image_data: bytes, mime_type: str = "image/jpeg") -> str:
        import base64
        prompt = self._get_image_prompt()
        base64_image = base64.b64encode(image_data).decode("utf-8")

        try:
            # 尝试多模态，部分本地模型支持
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}
                    ]
                }]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"图片分析出错: {str(e)}（本地模型可能不支持图片）"

    def transcribe_audio(self, audio_data: bytes, mime_type: str = "audio/ogg") -> str:
        return "语音转录出错: 本地模型暂不支持语音转录，请使用 Gemini 或 OpenAI"


class ClaudeAnalyzer(BaseAnalyzer):
    """Anthropic Claude 分析器"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model_name = model

    def _chat(self, prompt: str) -> str:
        """发送聊天请求"""
        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    def analyze_idea(self, idea: str, available_models: list[str]) -> dict:
        models_list = "\n".join([f"- {m}" for m in available_models])
        prompt = self._get_analyze_idea_prompt(idea, models_list)

        try:
            text = self._chat(prompt)
            return self._parse_idea_analysis(text, available_models)
        except Exception as e:
            print(f"AI 分析错误: {e}")
            return {
                "matched_models": [],
                "tags": [],
                "analysis": f"分析时出错: {str(e)}",
                "suggested_new_model": None,
            }

    def generate_connection(self, idea1: str, idea2: str) -> str:
        prompt = self._get_connection_prompt(idea1, idea2)
        try:
            return self._chat(prompt).strip()
        except Exception as e:
            return f"分析时出错: {str(e)}"

    def generate_weekly_summary(self, ideas: list[dict], models_used: dict) -> str:
        prompt = self._get_weekly_summary_prompt(ideas, models_used)
        try:
            return self._chat(prompt).strip()
        except Exception as e:
            return f"生成周报时出错: {str(e)}"

    def search_mental_model(self, keyword: str) -> Optional[dict]:
        prompt = self._get_search_model_prompt(keyword)
        try:
            text = self._chat(prompt)
            return self._parse_model_search(text)
        except Exception as e:
            print(f"搜索思维模型出错: {e}")
            return None

    def analyze_image(self, image_data: bytes, mime_type: str = "image/jpeg") -> str:
        import base64
        prompt = self._get_image_prompt()
        base64_image = base64.b64encode(image_data).decode("utf-8")

        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": base64_image}},
                        {"type": "text", "text": prompt}
                    ]
                }]
            )
            return response.content[0].text.strip()
        except Exception as e:
            return f"图片分析出错: {str(e)}"

    def transcribe_audio(self, audio_data: bytes, mime_type: str = "audio/ogg") -> str:
        # Claude 目前不支持原生音频，返回提示
        return "语音转录出错: Claude 暂不支持语音转录，请使用 Gemini 或 OpenAI"


def create_analyzer(provider: str, api_key: str, model: str = None, base_url: str = None) -> BaseAnalyzer:
    """
    创建 AI 分析器

    Args:
        provider: AI 提供商 (gemini, openai, claude, grok, local)
        api_key: API Key
        model: 模型名称（可选，不指定则使用默认）
        base_url: API 地址（仅 local 需要）

    Returns:
        对应的分析器实例
    """
    provider = provider.lower()

    if provider == "gemini":
        return GeminiAnalyzer(api_key, model or "gemini-2.5-flash")
    elif provider == "openai":
        return OpenAIAnalyzer(api_key, model or "gpt-4o-mini")
    elif provider == "claude":
        return ClaudeAnalyzer(api_key, model or "claude-sonnet-4-20250514")
    elif provider == "grok":
        return GrokAnalyzer(api_key, model or "grok-2-latest")
    elif provider == "local":
        return LocalAnalyzer(api_key, model or "qwen2.5:7b", base_url or "http://localhost:11434/v1")
    else:
        raise ValueError(f"不支持的 AI 提供商: {provider}，可选: gemini, openai, claude, grok, local")


# 保持向后兼容
class IdeaAnalyzer(GeminiAnalyzer):
    """兼容旧版本的别名"""
    def __init__(self, api_key: str):
        super().__init__(api_key, "gemini-2.5-flash")
