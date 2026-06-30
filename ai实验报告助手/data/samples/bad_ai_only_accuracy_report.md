# 人工智能实验报告：KNN 分类实验

## 实验目的

使用 KNN 模型对鸢尾花数据集进行分类，并查看准确率。

## 实验环境

Python，sklearn。

## 实验代码

```python
from sklearn.datasets import load_iris
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score

data = load_iris()
X = data.data
y = data.target

model = KNeighborsClassifier(n_neighbors=5)
model.fit(X, y)
pred = model.predict(X)
print(accuracy_score(y, pred))
```

## 运行结果

```text
Accuracy: 0.9667
```

## 结果分析

准确率比较高，说明模型效果较好。

## 实验总结

本实验学会了使用 KNN 模型进行分类。

## 已知缺陷设计说明

该样例故意保留以下问题，用于测试系统是否能发现 AI/机器学习报告中的典型缺陷：

- 没有划分训练集和测试集，直接在训练数据上评估，存在数据泄漏风险。
- 没有说明是否进行特征标准化。
- 只报告准确率，没有混淆矩阵、分类报告或错误样本分析。
- 没有比较不同 K 值。
- 结果分析过于简单，不能说明模型为什么有效或可能在哪些类别出错。
