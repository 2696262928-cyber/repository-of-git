COURSE_KEYWORDS = {
    "programming": {
        "course_name": "程序设计",
        "keywords": ["python", "java", "c++", "函数", "变量", "循环", "数组", "报错", "输入输出"],
    },
    "data_structure": {
        "course_name": "数据结构与算法",
        "keywords": ["链表", "栈", "队列", "二叉树", "图", "排序", "查找", "递归", "复杂度"],
    },
    "database": {
        "course_name": "数据库",
        "keywords": ["sql", "select", "insert", "update", "delete", "表结构", "主键", "外键", "事务"],
    },
    "operating_system": {
        "course_name": "操作系统",
        "keywords": ["进程", "线程", "调度", "死锁", "内存管理", "文件系统", "信号量", "互斥"],
    },
    "computer_network": {
        "course_name": "计算机网络",
        "keywords": ["tcp", "udp", "ip", "http", "dns", "路由", "抓包", "wireshark", "报文"],
    },
    "ai_ml": {
        "course_name": "人工智能与机器学习",
        "keywords": ["knn", "神经网络", "训练集", "测试集", "准确率", "损失", "模型", "分类"],
    },
    "embedded_system": {
        "course_name": "嵌入式系统",
        "keywords": ["uart", "spi", "dma", "adc", "pwm", "gpio", "timer", "oled", "w25q128", "flash", "cubemx", "hal_"],
    },
}


def classify_course_by_rules(text: str) -> dict:
    lower_text = text.lower()
    scores = {}
    for course_type, meta in COURSE_KEYWORDS.items():
        score = 0
        for keyword in meta["keywords"]:
            score += lower_text.count(keyword.lower())
        scores[course_type] = score

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]
    if best_score == 0:
        return {
            "course_type": "unknown",
            "course_name": "无法判断",
            "confidence": 0,
            "reason": "未匹配到足够的课程关键词。",
        }

    total = sum(scores.values())
    confidence = round(best_score / total, 2) if total else 0
    return {
        "course_type": best_type,
        "course_name": COURSE_KEYWORDS[best_type]["course_name"],
        "confidence": confidence,
        "reason": f"关键词匹配得分最高：{best_score}。",
    }
