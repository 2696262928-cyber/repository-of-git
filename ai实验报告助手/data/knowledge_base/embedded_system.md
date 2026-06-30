# 嵌入式系统课程知识库

本文件用于“嵌入式系统类实验报告”的 RAG 检索增强。内容参考 FreeRTOS、Arm/CMSIS 文档等公开资料，并结合 MCU 外设、实时任务、通信和中断实验改写为评分参考。它关注硬件连接、时序、资源限制、实时性和可复现验证。

## 报告结构与评分关注点

嵌入式实验报告应包含：实验目的、硬件平台、软件环境、接线图或引脚表、外设配置、程序流程、关键代码、运行结果、波形/串口/逻辑分析仪证据、问题分析和总结。评阅时重点看“硬件连接是否清楚”“外设参数是否完整”“是否验证实时性和稳定性”“是否说明异常和调试过程”。

高质量报告会写明 MCU 型号、开发板、编译器/IDE、时钟频率、引脚复用、供电方式、传感器型号、通信参数和固件版本。若报告只有代码截图，没有接线和运行证据，难以复现实验。

## GPIO、定时器、ADC、PWM 与串口外设

基础外设实验应说明寄存器或 HAL/API 配置含义。GPIO 实验应说明输入输出模式、上拉下拉、消抖和电平逻辑；定时器实验应说明时钟源、预分频、计数周期和中断周期；ADC 实验应说明采样通道、分辨率、参考电压和采样频率；PWM 实验应说明频率、占空比和输出引脚；UART 实验应说明波特率、数据位、校验位和停止位。

评分时可关注：是否给出参数计算过程；是否展示串口输出、波形或传感器数据；是否说明误差来源；是否避免阻塞延时影响实时性；是否处理外设初始化失败。若只调用初始化函数而没有解释参数，应提示补充配置依据。

## 中断、NVIC、SysTick 与实时响应

中断实验应说明中断源、触发方式、优先级、服务函数和共享数据保护。Arm Cortex-M 的 NVIC 支持中断优先级管理，数值越小通常表示更高紧急程度，但具体优先级位数由芯片实现决定。SysTick 常用于系统节拍或定时基准。

评阅时应检查：是否说明中断触发条件；ISR 中是否避免长时间阻塞、打印和复杂计算；主循环与中断之间共享变量是否使用 `volatile` 或同步机制；是否记录响应时间或抖动；是否解释优先级嵌套。若中断服务函数过长导致系统卡顿，应提示实时性问题。

## RTOS 任务、优先级与调度

FreeRTOS 等 RTOS 实验应说明任务创建、栈大小、优先级、任务状态和调度策略。FreeRTOS 文档说明，就绪或运行状态的高优先级任务会优先获得 CPU 时间；同优先级任务可根据配置进行时间片轮转。报告应展示任务周期、优先级关系和运行日志。

评分时可关注：是否解释任务阻塞、就绪、运行、挂起状态；是否合理设置延时和周期；是否避免高优先级任务忙等导致低优先级任务饥饿；是否说明栈溢出检查；是否用时间戳或 GPIO 翻转验证调度。若只创建任务但不分析调度现象，应判为分析不足。

## 队列、信号量、互斥锁、事件组与任务通知

RTOS 同步通信实验应说明使用哪种机制以及原因。队列适合在任务或中断之间传递数据；二值信号量常用于事件同步；计数信号量可管理多个同类资源；互斥锁用于保护共享资源；事件组适合等待多个事件位；任务通知适合单一接收任务的轻量事件通知。

评阅时应检查：是否说明生产者和消费者关系；是否处理队列满、队列空和超时；ISR 中是否使用 FromISR 版本 API；互斥锁是否避免优先级反转；是否记录同步前后的运行差异。若共享变量没有保护，或者在中断中调用非 ISR 安全 API，应提示风险。

## 通信接口与协议实验

常见通信实验包括 UART、I2C、SPI、CAN、蓝牙、Wi-Fi、MQTT 等。报告应说明通信拓扑、主从关系、时钟、地址、速率、数据帧格式、校验和错误处理。若使用传感器，应提供数据手册关键参数、寄存器地址和读取流程。

评分时可关注：是否展示逻辑分析仪或串口日志；是否说明丢包、超时、校验失败处理；是否区分总线电平和协议帧；是否说明端序、数据类型转换和单位换算。若只展示最终数据，不说明通信过程，应提示证据不足。

## 资源限制、低功耗与稳定性

嵌入式系统受 CPU、RAM、Flash、功耗和实时性限制。报告应关注栈大小、堆使用、全局变量、动态内存、任务周期、最坏响应时间和功耗模式。若实验涉及低功耗，应说明进入/退出睡眠的条件、唤醒源和功耗测量方法。

评阅时可检查：是否有内存占用或栈余量说明；是否避免无限阻塞；是否处理看门狗；是否进行长时间运行测试；是否说明异常复位、串口乱码、传感器无响应等调试过程。若只在短时间演示成功，缺少稳定性验证，应提示补充。

## 典型实验任务与检索关键词

常见嵌入式实验包括 LED 闪烁、按键中断、串口收发、PWM 调光、ADC 采样、定时器中断、I2C/SPI 传感器读取、OLED 显示、FreeRTOS 多任务、队列通信、信号量同步、低功耗唤醒和看门狗。检索时可关注“引脚、GPIO、定时器、预分频、占空比、ADC、UART、波特率、中断、NVIC、任务优先级、队列、信号量、FromISR、栈大小”等关键词。

若报告出现“按键中断”，重点检查触发沿、消抖、中断服务函数和共享变量。若出现“串口”，重点检查波特率、帧格式和日志输出。若出现“PWM”，重点检查频率和占空比计算。若出现“FreeRTOS”，重点检查任务状态、优先级、阻塞延时和同步机制。若出现“传感器”，重点检查总线地址、寄存器和单位换算。

## 常见扣分点

- 没有硬件型号、引脚连接、供电和软件版本。
- 外设参数没有计算过程或依据。
- 只有代码截图，没有串口、波形、照片或运行日志。
- ISR 中执行过多耗时操作。
- RTOS 任务优先级设置不合理，导致任务饥饿。
- 队列、信号量、互斥锁使用场景混淆。
- 未说明异常处理、超时处理和资源释放。

## 参考来源

- FreeRTOS Documentation Overview: https://www.freertos.org/Documentation/00-Overview
- FreeRTOS Task Priorities: https://www.freertos.org/Documentation/02-Kernel/02-Kernel-features/01-Tasks-and-co-routines/03-Task-priorities
- FreeRTOS Scheduling: https://www.freertos.org/Documentation/02-Kernel/02-Kernel-features/01-Tasks-and-co-routines/04-Task-scheduling
- FreeRTOS Queues: https://freertos.org/Documentation/02-Kernel/02-Kernel-features/02-Queues-mutexes-and-semaphores/01-Queues
- FreeRTOS Task Notifications: https://www.freertos.org/Documentation/02-Kernel/02-Kernel-features/03-Direct-to-task-notifications/01-Task-notifications
- Arm CMSIS NVIC Documentation: https://arm-software.github.io/CMSIS_5/Core/html/group__NVIC__gr.html
- Arm Cortex-M NVIC register documentation: https://developer.arm.com/documentation/ddi0337/e/Nested-Vectored-Interrupt-Controller/NVIC-programmer-s-model/NVIC-register-descriptions
