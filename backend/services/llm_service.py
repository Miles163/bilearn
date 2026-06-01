import json
import re
import urllib.request
from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL

BASE_PROMPT = """你是一个专业的学习助手。根据用户提供的视频字幕，提取关键信息并以 JSON 格式返回。

{lang_instruction}

返回格式严格如下（必须合法 JSON，不要加 markdown 代码块标记）：
{{
  "summary": "详细的视频内容总结",
  "key_points": [
    "知识点1：详细说明",
    "知识点2：详细说明",
    ...
  ],
  "cards": [
    {{"question": "复习问题", "answer": "详细答案"}}
  ],
  "cleaned_subtitle": "精校版字幕文本",
  "translated_subtitle": "双语对照字幕"
}}

要求：
- **summary**：中文。用 **标题式分段** 呈现，结构清晰。格式：先一段总览概述，再分几大主题，每个主题用 `【主题名】` 开头，下面用 - 列举要点。重点内容用 **加粗** 标出。覆盖视频所有重要内容，500-800字。
- **key_points**：中文。提取 6-12 个具体知识点，每个包含编号+详细说明。
- **cards**：中文。生成 5-8 个高质量的问答复习卡片，覆盖视频核心内容。
- **cleaned_subtitle**：不要压缩！不要概括！仅去除口语词（嗯、啊、那个、那么、you know、like、basically等），修正标点和断句，保留全部原文信息量。按原文段落分段（用 \n\n 分隔）。
- **translated_subtitle**：非中文视频才填此项。**双语对照格式**：把 cleaned_subtitle 按段落组织，**每段先英文原文，再空一行，再中文翻译**，段与段之间用 \n\n\n 分隔。中文视频此字段留空字符串。
- 如果字幕为空或过短，返回 {{"summary": "", "key_points": [], "cards": [], "cleaned_subtitle": "", "translated_subtitle": ""}}
"""

LANG_CONFIGS = {
    "zh": {
        "lang_instruction": "字幕是中文。cleaned_subtitle 输出中文精校版分段。translated_subtitle 留空。",
        "summary_desc": "500-800字",
    },
    "en": {
        "lang_instruction": "字幕是英文。cleaned_subtitle 输出英文精校版（分段）。translated_subtitle 输出双语对照（每段：英文原文 → 空行 → 中文翻译）。",
        "summary_desc": "500-800字",
    },
    "other": {
        "lang_instruction": "字幕不是中文或英文。cleaned_subtitle 输出原文精校版（分段）。translated_subtitle 输出双语对照（每段：原文 → 空行 → 中文翻译）。",
        "summary_desc": "500-800字",
    },
}


def _detect_lang(text: str) -> str:
    try:
        from langdetect import detect
        lang = detect(text[:500])
        if lang in ("zh-cn", "zh-tw", "zh"):
            return "zh"
        elif lang == "en":
            return "en"
        return "other"
    except Exception:
        return "zh"


def _build_system_prompt(subtitle: str) -> str:
    lang = _detect_lang(subtitle)
    config = LANG_CONFIGS.get(lang, LANG_CONFIGS["other"])
    return BASE_PROMPT.format(**config)


DEEPSEEK_PRICES = {"input": 0.14 / 1_000_000, "output": 0.28 / 1_000_000}


def _calc_cost(usage: dict) -> float:
    return usage.get("prompt_tokens", 0) * DEEPSEEK_PRICES["input"] + usage.get("completion_tokens", 0) * DEEPSEEK_PRICES["output"]


def generate_notes(subtitle: str) -> tuple[dict, dict]:
    """Returns (note_data, {"prompt_tokens":N, "completion_tokens":N, "total_tokens":N, "cost":N.NNNN})"""
    if not subtitle or len(subtitle.strip()) < 20:
        return ({"summary": "", "key_points": [], "cards": [], "cleaned_subtitle": ""}, {})

    if not DEEPSEEK_API_KEY:
        return {"summary": "请设置 DEEPSEEK_API_KEY 环境变量以启用 AI 笔记生成",
                "key_points": [],
                "cleaned_subtitle": "",
                "translated_subtitle": "",
                "cards": []}, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "cost": 0}

    system_prompt = _build_system_prompt(subtitle)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": subtitle[:6000]},
    ]

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 4096,
    }

    url = f"{DEEPSEEK_BASE_URL}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    }

    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read())
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            usage["cost"] = round(_calc_cost(usage), 6)
            if not content:
                return ({"summary": "", "key_points": [], "cards": [], "cleaned_subtitle": ""}, usage)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            brace_start = content.find("{")
            brace_end = content.rfind("}")
            if brace_start >= 0 and brace_end > brace_start:
                content = content[brace_start:brace_end+1]
            content = re.sub(r'[\x00-\x1f\x7f]', '', content)
            return (json.loads(content), usage)
    except Exception as e:
        raise RuntimeError(f"AI 处理出错: {e}")
