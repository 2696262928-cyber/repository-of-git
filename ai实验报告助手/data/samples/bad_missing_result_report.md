# 缺陷样例：排序算法实验

## 实验目的

掌握冒泡排序和选择排序的基本思想。

## 实验环境

Python 3.11

## 实验原理

冒泡排序通过相邻元素比较和交换，将较大的元素逐步移动到序列末尾。选择排序每轮选择最小元素放到当前位置。

## 核心代码

```python
def bubble_sort(arr):
    for i in range(len(arr)):
        for j in range(0, len(arr) - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr
```

## 实验总结

本实验学习了排序算法。

