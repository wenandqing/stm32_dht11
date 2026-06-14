-- 1. 创建数据库
CREATE DATABASE IF NOT EXISTS TempHumidityDB;
USE TempHumidityDB;

-- 2. 设备表
CREATE TABLE Device (
    device_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '设备ID',
    device_name VARCHAR(50) NOT NULL COMMENT '设备名称',
    location VARCHAR(100) COMMENT '安装位置',
    ip_address VARCHAR(15) COMMENT 'IP地址',
    status ENUM('在线','离线','故障') DEFAULT '离线' COMMENT '设备状态',
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
);

-- 3. 传感器数据表（预留接收接口）
CREATE TABLE SensorData (
    data_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '数据ID',
    device_id INT NOT NULL COMMENT '设备ID',
    temperature DECIMAL(5,2) COMMENT '温度(℃)',
    humidity DECIMAL(5,2) COMMENT '湿度(%)',
    collect_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '采集时间',
    FOREIGN KEY (device_id) REFERENCES Device(device_id) ON DELETE CASCADE
);

-- 4. 用户表
CREATE TABLE User (
    user_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '用户ID',
    username VARCHAR(50) UNIQUE NOT NULL COMMENT '用户名',
    password VARCHAR(100) NOT NULL COMMENT '密码',
    role ENUM('admin','operator','viewer') DEFAULT 'viewer' COMMENT '角色',
    created_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
);

-- 5. 报警记录表
CREATE TABLE Alert (
    alert_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '报警ID',
    device_id INT NOT NULL COMMENT '设备ID',
    alert_type ENUM('温度过高','温度过低','湿度过高','湿度过低','设备离线') COMMENT '报警类型',
    alert_value DECIMAL(5,2) COMMENT '触发报警的数值',
    status ENUM('未处理','已处理','已忽略') DEFAULT '未处理' COMMENT '处理状态',
    alert_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '报警时间',
    handle_time DATETIME COMMENT '处理时间',
    handle_note VARCHAR(200) COMMENT '处理备注',
    FOREIGN KEY (device_id) REFERENCES Device(device_id) ON DELETE CASCADE
);

-- 6. 插入初始化数据
-- 插入设备
INSERT INTO Device (device_id, device_name, location, ip_address, status) VALUES
(1, '实验室温湿度采集仪', 'A栋101实验室', '192.168.1.100', '在线'),
(2, '机房温湿度监控器', '数据中心B区', '192.168.1.101', '在线');

-- 插入模拟数据（用于测试）
INSERT INTO SensorData (device_id, temperature, humidity, collect_time) VALUES
(1, 23.5, 55.0, '2024-06-01 08:00:00'),
(1, 24.0, 56.5, '2024-06-01 09:00:00'),
(1, 24.5, 57.0, '2024-06-01 10:00:00'),
(2, 22.0, 45.0, '2024-06-01 08:00:00'),
(2, 22.5, 46.0, '2024-06-01 09:00:00'),
(2, 23.0, 47.0, '2024-06-01 10:00:00');

-- 插入用户（默认密码均为123456，实际应使用加密存储）
INSERT INTO User (username, password, role) VALUES
('admin', '123456', 'admin'),
('operator', '123456', 'operator'),
('viewer', '123456', 'viewer');



-- 查询最新10条温湿度记录
SELECT d.device_name, s.temperature, s.humidity, s.collect_time
FROM SensorData s
JOIN Device d ON s.device_id = d.device_id
ORDER BY s.collect_time DESC
LIMIT 10;

-- 统计每台设备的平均温湿度
SELECT d.device_name, 
       AVG(s.temperature) AS avg_temp, 
       AVG(s.humidity) AS avg_hum
FROM SensorData s
JOIN Device d ON s.device_id = d.device_id
GROUP BY d.device_id;

-- 按日期统计每日数据量
SELECT DATE(collect_time) AS date, 
       COUNT(*) AS record_count,
       MIN(temperature) AS min_temp,
       MAX(temperature) AS max_temp
FROM SensorData
GROUP BY DATE(collect_time);



-- 硬件上报数据时的插入语句（应用程序调用）
INSERT INTO SensorData (device_id, temperature, humidity, collect_time)
VALUES (1, 25.5, 60.0, NOW());
-- 批量插入
INSERT INTO SensorData (device_id, temperature, humidity, collect_time) VALUES
(1, 25.3, 59.8, NOW()),
(2, 22.1, 44.5, NOW());



-- 删除指定设备的所有历史数据
DELETE FROM SensorData WHERE device_id = 1;
-- 删除7天前的旧数据（清理历史）
DELETE FROM SensorData WHERE collect_time < DATE_SUB(NOW(), INTERVAL 7 DAY);



-- 创建两个不同权限的账户
-- 账户1: 只读账户（仅查询权限）
CREATE USER 'readonly_user'@'localhost' IDENTIFIED BY 'read123';
GRANT SELECT ON TempHumidityDB.* TO 'readonly_user'@'localhost';

-- 账户1: 修改只读账户连接权限，任意IP可连接
DROP USER IF EXISTS 'readonly_user'@'%';
CREATE USER 'readonly_user'@'%' IDENTIFIED BY 'read123';
GRANT SELECT ON TempHumidityDB.* TO 'readonly_user'@'%';
FLUSH PRIVILEGES;

-- 账户2: 数据操作账户（增删改查权限）
CREATE USER 'data_user'@'localhost' IDENTIFIED BY 'data456';
GRANT SELECT, INSERT, UPDATE, DELETE ON TempHumidityDB.* TO 'data_user'@'localhost';

-- 账户2: 修改数据操作账户连接权限，任意IP可连接
DROP USER IF EXISTS 'data_user'@'%';
CREATE USER 'data_user'@'%' IDENTIFIED BY 'data456';
GRANT SELECT, INSERT, UPDATE, DELETE ON TempHumidityDB.* TO 'data_user'@'%';
FLUSH PRIVILEGES;


-- 刷新权限
FLUSH PRIVILEGES;

-- 验证权限
-- 使用 readonly_user 登录后，只能执行 SELECT，不能 INSERT/UPDATE/DELETE
-- 使用 data_user 登录后，可以执行所有数据操作