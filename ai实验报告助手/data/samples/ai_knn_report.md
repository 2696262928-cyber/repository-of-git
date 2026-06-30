# 人工智能实验报告：KNN 鸢尾花分类

## 实验目的

本实验使用 K 近邻（K-Nearest Neighbors, KNN）算法完成 Iris 鸢尾花数据集分类任务，目标包括：

1. 理解 KNN 基于距离度量和多数投票的分类思想。
2. 掌握训练集、测试集划分和特征标准化流程。
3. 比较不同 K 值对模型效果的影响。
4. 使用准确率、混淆矩阵、分类报告等指标评价分类模型。
5. 分析模型误分类原因和实验局限。

## 实验环境

- 操作系统：Windows 11
- Python：3.11
- 主要库：scikit-learn 1.4、numpy、pandas、matplotlib
- 数据集：scikit-learn 内置 Iris 鸢尾花数据集
- 随机种子：`random_state=42`

## 数据集说明

Iris 数据集包含 150 条样本，每条样本有 4 个特征：

| 特征 | 含义 |
| --- | --- |
| sepal length | 萼片长度 |
| sepal width | 萼片宽度 |
| petal length | 花瓣长度 |
| petal width | 花瓣宽度 |

标签共有 3 类：

- setosa
- versicolor
- virginica

每类各 50 条样本，类别分布均衡。由于不同特征的量纲和取值范围不同，实验中需要对特征进行标准化，避免距离计算被某一维度主导。

## 实验原理

KNN 是一种基于实例的监督学习算法。对于一个待分类样本，算法计算它与训练集中各样本的距离，选择距离最近的 K 个邻居，并根据邻居类别进行多数投票。

本实验使用欧氏距离：

```text
d(x, y) = sqrt(sum((x_i - y_i)^2))
```

K 值会影响模型偏差和方差：

- K 过小：模型容易受噪声影响，可能过拟合。
- K 过大：决策边界过于平滑，可能欠拟合。
- 合理 K 值需要通过验证集或交叉验证选择。

## 实验步骤

1. 加载 Iris 数据集，查看样本数量、特征维度和类别分布。
2. 使用 `train_test_split` 按 7:3 划分训练集和测试集。
3. 使用 `stratify=y` 保持训练集和测试集中的类别比例一致。
4. 使用 `StandardScaler` 在训练集上 `fit`，再分别转换训练集和测试集。
5. 分别训练 K=1、3、5、7、9 的 KNN 模型。
6. 记录不同 K 值的测试集准确率。
7. 对最佳模型输出混淆矩阵和分类报告。
8. 分析误分类样本和模型局限。

## 核心代码

```python
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report

iris = load_iris()
X, y = iris.data, iris.target

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.3,
    random_state=42,
    stratify=y,
)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

results = []
for k in [1, 3, 5, 7, 9]:
    model = KNeighborsClassifier(n_neighbors=k)
    model.fit(X_train_scaled, y_train)
    y_pred = model.predict(X_test_scaled)
    acc = accuracy_score(y_test, y_pred)
    results.append((k, acc))
    print(k, acc)

best_model = KNeighborsClassifier(n_neighbors=5)
best_model.fit(X_train_scaled, y_train)
y_pred = best_model.predict(X_test_scaled)

print(confusion_matrix(y_test, y_pred))
print(classification_report(y_test, y_pred, target_names=iris.target_names))
```

## 运行结果

### 不同 K 值准确率

| K 值 | 测试集准确率 |
| ---: | ---: |
| 1 | 0.9556 |
| 3 | 0.9556 |
| 5 | 0.9778 |
| 7 | 0.9556 |
| 9 | 0.9556 |

本次实验中 K=5 取得最高测试集准确率，因此选择 K=5 作为最终模型。

### 混淆矩阵

```text
Confusion Matrix:
[[15  0  0]
 [ 0 14  1]
 [ 0  0 15]]
```

### 分类报告

```text
              precision    recall  f1-score   support

setosa            1.00      1.00      1.00        15
versicolor        1.00      0.93      0.97        15
virginica         0.94      1.00      0.97        15

accuracy                              0.98        45
macro avg         0.98      0.98      0.98        45
weighted avg      0.98      0.98      0.98        45
```

## 结果分析

模型整体准确率为 97.78%，45 个测试样本中只有 1 个样本被误分类。从混淆矩阵可以看出：

- setosa 类全部分类正确，说明该类别与其他两类在特征空间中区分明显。
- versicolor 有 1 个样本被预测为 virginica，说明这两个类别的部分样本在花瓣长度和花瓣宽度上较接近。
- virginica 全部被正确识别，但 precision 为 0.94，原因是有一个 versicolor 被误判为 virginica。

不同 K 值实验表明，K=1 和 K=3 对局部样本更敏感，K=7 和 K=9 可能使决策边界过于平滑。本实验中 K=5 在当前划分下效果最好，但由于数据集规模较小，单次训练/测试划分可能存在偶然性。

## 局限性与改进方向

1. 本实验只使用一次训练/测试划分，后续可以使用 5 折或 10 折交叉验证选择 K 值。
2. 当前只使用欧氏距离，可以尝试曼哈顿距离或距离加权投票。
3. Iris 数据集规模较小，不能代表复杂真实数据场景。
4. 可以绘制二维特征空间下的决策边界，进一步观察不同 K 值对分类边界的影响。
5. 可以输出误分类样本的原始特征，分析其与相邻类别样本的距离关系。

## 实验总结

通过本实验，我掌握了 KNN 分类流程，包括数据划分、特征标准化、模型训练、参数比较和结果评价。实验说明 KNN 对特征尺度较敏感，必须注意标准化和参数选择。仅报告准确率不足以全面评价模型，还需要结合混淆矩阵、分类报告和误分类分析判断模型效果。
