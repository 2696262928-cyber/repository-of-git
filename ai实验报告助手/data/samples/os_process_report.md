# 操作系统实验报告：时间片轮转调度模拟

## 实验目的

理解进程调度中的时间片轮转算法，掌握等待时间、周转时间和平均周转时间的计算方法。

## 实验环境

- 操作系统：Ubuntu 22.04
- 编程语言：C++
- 编译器：g++ 11

## 实验原理

时间片轮转调度将就绪队列中的进程按队列顺序分配 CPU，每个进程最多运行一个时间片。若进程未完成，则重新进入队尾等待。

## 核心代码

```cpp
while (!q.empty()) {
    int i = q.front();
    q.pop();
    int run = min(quantum, remain[i]);
    current += run;
    remain[i] -= run;
    if (remain[i] > 0) {
        q.push(i);
    } else {
        finish[i] = current;
    }
}
```

## 运行结果

```text
时间片 quantum = 2
P1 burst=5 finish=9 turnaround=9
P2 burst=3 finish=8 turnaround=8
P3 burst=1 finish=5 turnaround=5
平均周转时间：7.33
```

## 结果分析

时间片较小时，短进程能较快获得响应，但上下文切换次数增加。P3 的运行时间最短，因此在第二轮前完成，周转时间最低。

## 实验总结

通过本实验，我理解了轮转调度的公平性和时间片大小对系统响应时间的影响。后续可加入到达时间不同的情况。

