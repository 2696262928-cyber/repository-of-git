# 计算机网络实验报告：HTTP 抓包分析

## 实验目的

掌握 Wireshark 抓包方法，理解 HTTP 请求响应结构、TCP 三次握手和常见状态码含义。

## 实验环境

- 操作系统：Windows 11
- 抓包工具：Wireshark 4.2
- 浏览器：Chrome
- 过滤条件：`http || tcp.port == 80`

## 实验步骤

1. 打开 Wireshark 并选择无线网卡。
2. 启动抓包后访问测试页面。
3. 使用过滤条件筛选 HTTP 和 TCP 报文。
4. 观察 TCP 三次握手过程。
5. 展开 HTTP 请求头和响应头字段。

## 运行结果

```text
TCP SYN: client -> server, Seq=0
TCP SYN ACK: server -> client, Seq=0, Ack=1
TCP ACK: client -> server, Ack=1
HTTP GET /index.html
HTTP/1.1 200 OK
Content-Type: text/html
```

## 结果分析

抓包结果显示客户端先通过 TCP 三次握手建立连接，再发送 HTTP GET 请求。服务器返回 `200 OK`，表示资源请求成功。`Content-Type` 字段说明响应体类型为 HTML 文档。

## 实验总结

本实验帮助我理解了 HTTP 工作在 TCP 连接之上，抓包字段能够直接对应协议原理。后续可继续分析 DNS 解析和 HTTPS TLS 握手。

