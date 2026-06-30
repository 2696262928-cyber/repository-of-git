# 数据库实验报告：学生选课系统查询与事务分析

## 实验目的

本实验围绕学生选课系统完成数据库设计、SQL 查询、事务验证和索引分析，目标包括：

1. 掌握关系数据库表结构设计方法。
2. 理解主键、外键、非空约束和联合主键的作用。
3. 使用 JOIN、GROUP BY、HAVING 和聚合函数完成统计查询。
4. 验证外键约束和事务回滚对数据一致性的影响。
5. 使用索引和 EXPLAIN 初步分析查询性能。

## 实验环境

- 数据库：MySQL 8.0
- 客户端：DBeaver
- 字符集：utf8mb4
- 数据规模：学生 5 条、课程 4 条、选课记录 12 条
- 操作系统：Windows 11

## 业务背景与 ER 设计

系统包含学生、课程和选课记录三个实体：

- 一个学生可以选择多门课程。
- 一门课程可以被多个学生选择。
- 学生和课程之间是多对多关系，因此使用 `enrollment` 作为中间表。

关系模式如下：

```text
student(student_id, name, major)
course(course_id, course_name, credit)
enrollment(student_id, course_id, score)
```

其中：

- `student.student_id` 是学生表主键。
- `course.course_id` 是课程表主键。
- `enrollment(student_id, course_id)` 是联合主键。
- `enrollment.student_id` 和 `enrollment.course_id` 分别引用学生表和课程表。

## 表结构设计

```sql
CREATE TABLE student (
  student_id INT PRIMARY KEY,
  name VARCHAR(32) NOT NULL,
  major VARCHAR(64) NOT NULL
);

CREATE TABLE course (
  course_id INT PRIMARY KEY,
  course_name VARCHAR(64) NOT NULL,
  credit INT NOT NULL CHECK (credit > 0)
);

CREATE TABLE enrollment (
  student_id INT NOT NULL,
  course_id INT NOT NULL,
  score DECIMAL(5,2),
  PRIMARY KEY (student_id, course_id),
  FOREIGN KEY (student_id) REFERENCES student(student_id),
  FOREIGN KEY (course_id) REFERENCES course(course_id),
  CHECK (score IS NULL OR (score >= 0 AND score <= 100))
);
```

## 测试数据

```sql
INSERT INTO student VALUES
(1001, '张三', '计算机科学与技术'),
(1002, '李四', '软件工程'),
(1003, '王五', '人工智能'),
(1004, '赵六', '网络工程'),
(1005, '陈七', '数据科学');

INSERT INTO course VALUES
(1, '数据库系统', 3),
(2, '数据结构', 4),
(3, '计算机网络', 3),
(4, '人工智能导论', 2);

INSERT INTO enrollment VALUES
(1001, 1, 88.00), (1001, 2, 84.00), (1001, 3, 86.00),
(1002, 1, 75.00), (1002, 3, 82.00),
(1003, 1, 92.00), (1003, 2, 91.00), (1003, 4, 93.00),
(1004, 2, 70.00), (1004, 3, 77.00),
(1005, 1, 89.00), (1005, 4, 95.00);
```

## 实验步骤

1. 创建学生表、课程表和选课表。
2. 插入测试数据。
3. 查询每名学生的平均成绩。
4. 查询选课人数最多的课程。
5. 查询平均分大于 85 的学生。
6. 验证外键约束能阻止不存在学生的选课记录。
7. 使用事务模拟成绩修改并执行回滚。
8. 为选课表课程编号建立索引，并使用 EXPLAIN 查看查询计划。

## 查询语句与结果

### 查询每名学生平均成绩

```sql
SELECT s.student_id, s.name, AVG(e.score) AS avg_score
FROM student s
JOIN enrollment e ON s.student_id = e.student_id
GROUP BY s.student_id, s.name
ORDER BY avg_score DESC;
```

运行结果：

```text
student_id | name | avg_score
1003       | 王五 | 92.00
1005       | 陈七 | 92.00
1001       | 张三 | 86.00
1002       | 李四 | 78.50
1004       | 赵六 | 73.50
```

### 查询选课人数最多的课程

```sql
SELECT c.course_id, c.course_name, COUNT(*) AS student_count
FROM course c
JOIN enrollment e ON c.course_id = e.course_id
GROUP BY c.course_id, c.course_name
ORDER BY student_count DESC
LIMIT 1;
```

运行结果：

```text
course_id | course_name | student_count
1         | 数据库系统   | 4
```

### 查询平均分大于 85 的学生

```sql
SELECT s.student_id, s.name, AVG(e.score) AS avg_score
FROM student s
JOIN enrollment e ON s.student_id = e.student_id
GROUP BY s.student_id, s.name
HAVING AVG(e.score) > 85
ORDER BY avg_score DESC;
```

运行结果：

```text
student_id | name | avg_score
1003       | 王五 | 92.00
1005       | 陈七 | 92.00
1001       | 张三 | 86.00
```

## 约束验证

插入不存在学生编号的选课记录：

```sql
INSERT INTO enrollment VALUES (9999, 1, 80.00);
```

运行结果：

```text
ERROR 1452: Cannot add or update a child row: a foreign key constraint fails
```

说明外键约束可以阻止不存在学生的选课记录进入数据库，保证引用完整性。

## 事务实验

本实验使用事务模拟成绩修改：

```sql
START TRANSACTION;

UPDATE enrollment
SET score = 60.00
WHERE student_id = 1001 AND course_id = 1;

SELECT score
FROM enrollment
WHERE student_id = 1001 AND course_id = 1;

ROLLBACK;

SELECT score
FROM enrollment
WHERE student_id = 1001 AND course_id = 1;
```

运行结果：

```text
事务中查询：60.00
回滚后查询：88.00
```

分析：事务中的更新在回滚后被撤销，说明事务原子性可以保证一组操作要么全部提交，要么全部撤销。本实验只在单会话中验证了回滚效果，后续可以增加两个会话并发实验，进一步观察隔离级别对可见性的影响。

## 索引与执行计划

为 `enrollment.course_id` 建立索引：

```sql
CREATE INDEX idx_enrollment_course ON enrollment(course_id);
```

查看查询计划：

```sql
EXPLAIN
SELECT c.course_name, COUNT(*) AS student_count
FROM course c
JOIN enrollment e ON c.course_id = e.course_id
GROUP BY c.course_name;
```

运行结果摘要：

```text
table: e
type: index
key: idx_enrollment_course
rows: 12
Extra: Using index
```

由于当前测试数据规模很小，索引带来的性能提升不明显，但执行计划显示查询可以使用课程编号索引。若数据规模扩大到数万条选课记录，索引对按课程统计的查询更有价值。

## 结果分析

本实验完成了学生选课系统的基本数据库设计和查询分析。联合主键可以避免同一学生重复选择同一课程，外键可以保证选课记录必须引用已存在的学生和课程。JOIN 查询可以把学生、课程和成绩关联起来，聚合函数适合统计平均成绩和选课人数。

事务实验说明 ROLLBACK 可以撤销未提交修改，但当前实验只验证了单会话回滚，没有完整展示 READ COMMITTED、REPEATABLE READ 等隔离级别差异。索引实验使用 EXPLAIN 观察到索引被使用，但由于数据量较小，性能对比证据仍然不足。

## 实验总结

通过本实验，我掌握了关系模式设计、约束设计、连接查询、聚合统计、事务回滚和索引分析的基本方法。后续改进方向包括：增加 ER 图截图，扩充并发事务实验，扩大数据规模后比较索引前后的查询耗时，并进一步分析不同隔离级别下的可见性变化。
