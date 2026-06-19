"""智能文本凝练模块。

不调用 LLM（太慢），用规则+关键词将长报告压缩为精华版：
- 保留章节标题、代码块、技术参数句、结果/结论段落
- 压缩描述性段落（首句+末句）
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ── 关键词与模式 ────────────────────────────────────────

SECTION_TITLES = [
    "实验目的", "实验要求", "实验环境", "实验原理",
    "实验步骤", "实验过程", "核心代码", "运行结果",
    "实验结果", "结果分析", "实验总结", "参考资料",
    "objective", "requirements", "environment", "principle",
    "procedure", "results", "analysis", "conclusion", "references",
]

TECH_KEYWORDS = [
    # 嵌入式外设
    "uart", "spi", "i2c", "dma", "adc", "dac", "pwm", "timer",
    "gpio", "oled", "w25q128", "flash", "usart", "can", "i2s",
    # 配置/寄存器
    "main.c", "cubemx", "hal_", "callback", "interrupt",
    "prescaler", "period", "duty", "baud", "rcc", "nvic",
    # 测试
    "test", "testing", "verify", "measure", "debug",
]

# 技术参数正则
TECH_PARAM_PATTERNS = [
    (r"0x[0-9A-Fa-f]{2,}", "寄存器地址"),
    (r"\d+\.?\d*\s*(MHz|kHz|Hz|GHz)", "频率"),
    (r"\d+\.?\d*\s*(ms|us|ns|s|min)\b", "时间"),
    (r"\d+\.?\d*\s*(V|mV|kV)\b", "电压"),
    (r"\d+\.?\d*\s*(mA|A|uA)\b", "电流"),
    (r"\d{1,3}%\s*(占空|duty)", "占空比"),
    (r"\b(baud|bps)\s*\d+", "波特率"),
    (r"\b(pin|port|引脚)\s*[A-Z]?\d+", "引脚"),
    (r"\b(period|prescaler)\s*[=:]\s*\d+", "定时器参数"),
]

RESULT_SECTION_KEYWORDS = ["运行结果", "实验结果", "结果分析", "分析", "conclusion", "结论", "实验总结"]

# ── 数据类 ──────────────────────────────────────────────


@dataclass
class CondensationResult:
    original_length: int
    condensed_length: int
    condensed_text: str
    key_parameters: dict[str, list[str]] = field(default_factory=dict)
    preserved_code_blocks: int = 0
    preserved_sections: list[str] = field(default_factory=list)


# ── 核心函数 ────────────────────────────────────────────


def condense_report_text(text: str, target_length: int = 6000) -> CondensationResult:
    """将实验报告文本智能凝练，保留技术要点。

    Args:
        text: 原始报告全文。
        target_length: 目标字符数（软上限，可能略超以保留完整句子）。

    Returns:
        CondensationResult 含凝练后文本和提取的关键参数。
    """
    if len(text) <= target_length:
        return CondensationResult(
            original_length=len(text),
            condensed_length=len(text),
            condensed_text=text,
            key_parameters=extract_key_parameters(text),
        )

    lines = text.splitlines()
    preserved: list[str] = []
    code_block_count = 0

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 1. 代码块 — 完整保留
        if stripped.startswith("```") or stripped.startswith("~~~"):
            block_lines = [line]
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(("```", "~~~")):
                block_lines.append(lines[i])
                i += 1
            if i < len(lines):
                block_lines.append(lines[i])  # closing ```
            preserved.extend(block_lines)
            code_block_count += 1
            i += 1
            continue

        # 2. 章节标题 — 保留
        if _is_section_title(stripped):
            preserved.append(line)
            i += 1
            continue

        # 3. 含技术参数的句子 — 保留
        if _contains_tech_param(stripped):
            preserved.append(line)
            i += 1
            continue

        # 4. 含关键外设/寄存器名的句子 — 保留
        if _contains_tech_keyword(stripped):
            preserved.append(line)
            i += 1
            continue

        # 5. 结果/结论段落 — 保留原文
        if _is_in_result_section(stripped):
            preserved.append(line)
            # 保留整个段落
            i += 1
            while i < len(lines) and lines[i].strip() and not _is_section_title(lines[i].strip()):
                preserved.append(lines[i])
                i += 1
            continue

        # 6. 普通描述性段落 — 压缩
        if stripped:
            # 保留首句
            sentences = re.split(r"[。；;.]", stripped)
            if len(sentences) > 1:
                preserved.append(sentences[0] + "。")
                # 如果有末句且不同于首句，也保留
                last = sentences[-1].strip()
                if last and last != sentences[0].strip()[:len(last)]:
                    preserved.append(last + "。")
            else:
                preserved.append(stripped)
        i += 1

    condensed = "\n".join(preserved)
    key_params = extract_key_parameters(text)

    # 如果凝练后仍然太长，再做一次更激进的压缩
    if len(condensed) > target_length * 1.5:
        condensed = _aggressive_compress(condensed, target_length)

    return CondensationResult(
        original_length=len(text),
        condensed_length=len(condensed),
        condensed_text=condensed,
        key_parameters=key_params,
        preserved_code_blocks=code_block_count,
        preserved_sections=[s for s in SECTION_TITLES if s.lower() in condensed.lower()],
    )


def extract_key_parameters(text: str) -> dict[str, list[str]]:
    """从文本中提取按类别分组的技术参数。"""
    results: dict[str, list[str]] = {}
    for pattern, category in TECH_PARAM_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            unique = list(dict.fromkeys(m.strip() if isinstance(m, str) else m[0] for m in matches))
            results[category] = unique[:20]  # 每类最多 20 个
    return results


# ── 内部辅助 ────────────────────────────────────────────


def _is_section_title(line: str) -> bool:
    """判断是否为章节标题。"""
    line_lower = line.lower().strip(" #*-=~>")
    for title in SECTION_TITLES:
        if title in line_lower:
            return True
    # 匹配编号标题：1. 实验目的 / 二、实验原理
    if re.match(r"^[一二三四五六七八九十\d]+[、.．]\s*\S", line.strip()):
        return True
    return False


def _contains_tech_param(line: str) -> bool:
    """判断是否含技术参数（数字+单位）。"""
    for pattern, _ in TECH_PARAM_PATTERNS:
        if re.search(pattern, line, re.IGNORECASE):
            return True
    return False


def _contains_tech_keyword(line: str) -> bool:
    """判断是否含嵌入式/硬件关键词。"""
    line_lower = line.lower()
    return any(kw in line_lower for kw in TECH_KEYWORDS)


def _is_in_result_section(line: str) -> bool:
    """判断是否在结果/结论相关区域。"""
    line_lower = line.lower().strip(" #*-=~>")
    return any(kw in line_lower for kw in RESULT_SECTION_KEYWORDS)


def _aggressive_compress(text: str, target_length: int) -> str:
    """更激进地压缩：保留每个非空段落的前 40 字符。"""
    lines = text.splitlines()
    result = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if _is_section_title(stripped):
            result.append(line)
        elif _contains_tech_param(stripped):
            result.append(line)
        elif len(stripped) > 50:
            result.append(stripped[:50] + "...")
        else:
            result.append(stripped)
    return "\n".join(result)
