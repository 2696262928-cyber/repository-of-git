# 程序设计实验报告：学生成绩文件统计

## 实验目的

掌握 Python 文件读写、列表遍历、异常处理和基础统计方法，完成学生成绩文件的读取、平均分计算和等级统计。

## 实验环境

- 操作系统：Windows 11
- 编程语言：Python 3.11
- 开发工具：VS Code

## 实验步骤

1. 准备 `scores.txt`，每行格式为 `姓名,成绩`。
2. 使用 `open` 读取文件，按行解析姓名和成绩。
3. 对非法行进行跳过处理。
4. 统计平均分、最高分、最低分和及格人数。
5. 输出统计结果，并用边界数据进行测试。

## 核心代码

```python
def load_scores(path):
    records = []
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            parts = line.strip().split(",")
            if len(parts) != 2:
                continue
            name, score_text = parts
            try:
                score = float(score_text)
            except ValueError:
                continue
            records.append((name, score))
    return records


def summarize(records):
    scores = [score for _, score in records]
    return {
        "average": sum(scores) / len(scores),
        "max": max(scores),
        "min": min(scores),
        "pass_count": sum(score >= 60 for score in scores),
    }
```

## 运行结果

```text
平均分：78.40
最高分：96.00
最低分：52.00
及格人数：4
```

## 结果分析

程序能够正确忽略格式错误的输入行，并对合法成绩进行统计。对于空文件场景，目前 `summarize` 会因为除零而失败，后续应在调用前判断记录列表是否为空。

## 实验总结

通过本实验，我掌握了文本文件读取、字符串切分和异常处理。程序仍需补充空文件处理和更完整的单元测试。

