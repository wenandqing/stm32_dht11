# -*- coding: gbk -*-
from flask import Flask, request, jsonify
import pymysql
from datetime import datetime

app = Flask(__name__)

# ========== 数据库配置 ==========
DB_CONFIG = {
    'host': 'localhost',      # 数据库地址，本地就写localhost
    'user': 'data_user',      # 数据库用户名
    'password': 'data456',    # 数据库密码
    'database': 'TempHumidityDB',  # 数据库名
    'charset': 'utf8mb4'
}

# ========== 硬件数据接收接口 ==========
@app.route('/api/upload', methods=['POST'])
def upload_data():
    """
    ESP8266 调用这个接口来上报数据
    请求格式: POST /api/upload
    Body: {"device_id": 1, "temperature": 25.5, "humidity": 60.0}
    """
    try:
        # 1. 接收JSON数据
        data = request.get_json()
        
        # 调试打印，可以在终端看到收到的数据
        print(f"[收到数据] {data}")
        
        # 2. 提取字段（根据你ESP8266发送的格式调整）
        device_id = data.get('device_id', 1)      # 设备ID，默认1
        temperature = data.get('temperature')
        humidity = data.get('humidity')
        
        # 3. 校验数据
        if temperature is None or humidity is None:
            return jsonify({'status': 'error', 'message': '缺少temperature或humidity字段'}), 400
        
        # 4. 连接数据库并插入
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        sql = """
            INSERT INTO SensorData (device_id, temperature, humidity, collect_time)
            VALUES (%s, %s, %s, NOW())
        """
        cursor.execute(sql, (device_id, temperature, humidity))
        conn.commit()
        
        # 5. 关闭连接
        cursor.close()
        conn.close()
        
        # 6. 返回成功响应
        return jsonify({'status': 'success', 'message': '数据已存入数据库'}), 200
        
    except Exception as e:
        print(f"[错误] {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ========== 查询最新数据接口（可选，用于测试） ==========
@app.route('/api/latest', methods=['GET'])
def get_latest():
    """查询最新一条数据，方便测试验证"""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("""
            SELECT data_id, device_id, temperature, humidity, collect_time
            FROM SensorData
            ORDER BY collect_time DESC
            LIMIT 1
        """)
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ========== 启动服务 ==========
if __name__ == '__main__':
    # host='0.0.0.0' 表示允许外部设备（如ESP8266）访问
    # port=5000 是端口号
    app.run(host='0.0.0.0', port=5000, debug=True)
    