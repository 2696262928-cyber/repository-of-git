# 数据结构实验报告：栈的基本操作

## 实验目的

掌握栈这种后进先出线性结构的基本概念，理解入栈、出栈、取栈顶和判空操作的实现方式。

## 实验环境

- 操作系统：Windows 11
- 编程语言：Python 3
- 开发工具：VS Code

## 实验原理

栈是一种只能在一端进行插入和删除操作的线性表。允许插入和删除的一端称为栈顶，另一端称为栈底。栈的主要特点是后进先出。

## 实验步骤

1. 使用 Python 列表模拟栈结构。
2. 实现 push 方法完成入栈。
3. 实现 pop 方法完成出栈。
4. 实现 peek 方法查看栈顶元素。
5. 使用多组数据测试栈的后进先出特性。

## 核心代码

```python
class Stack:
    def __init__(self):
        self.items = []

    def push(self, item):
        self.items.append(item)

    def pop(self):
        if not self.items:
            return None
        return self.items.pop()

    def peek(self):
        if not self.items:
            return None
        return self.items[-1]

    def is_empty(self):
        return len(self.items) == 0


stack = Stack()
stack.push(1)
stack.push(2)
stack.push(3)
print(stack.pop())
print(stack.pop())
print(stack.pop())
```

## 运行结果

```text
3
2
1
```

## 结果分析

程序先后将 1、2、3 压入栈中，出栈时依次输出 3、2、1，符合栈的后进先出特点。`pop` 和 `peek` 方法都对空栈进行了判断，可以避免直接访问空列表导致异常。

## 实验总结

通过本实验，我理解了栈的基本操作和后进先出特性。使用 Python 列表可以较方便地模拟栈结构，但在更复杂的场景中还需要考虑异常处理、数据规模和接口设计。
