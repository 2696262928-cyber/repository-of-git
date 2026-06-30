# 缺陷样例：数据库查询实验

```sql
CREATE TABLE user_info (
  id INT PRIMARY KEY,
  name VARCHAR(20),
  age INT
);

INSERT INTO user_info VALUES (1, 'Alice', 20);
INSERT INTO user_info VALUES (2, 'Bob', 21);

SELECT * FROM user_info WHERE age >= 20;
```

```text
1 Alice 20
2 Bob 21
```

