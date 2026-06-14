// driver_wifi.c
#include "driver_wifi.h"
#include "driver_usart.h"
#include <string.h>
#include <stdio.h>

extern UART_HandleTypeDef huart2;
extern UART_HandleTypeDef huart1;

// 发送 AT 指令 (自动添加 \r\n)
void ESP8266_SendCmd(const char* cmd)
{
    HAL_UART_Transmit(&huart2, (uint8_t*)cmd, strlen(cmd), 100);
    HAL_UART_Transmit(&huart2, (uint8_t*)"\r\n", 2, 100);
}

// 等待指定响应 (带超时)
uint8_t ESP8266_WaitResponse(const char* expected, uint32_t timeout_ms)
{
    uint8_t rx_buffer[256];
    uint32_t start = HAL_GetTick();
    uint16_t index = 0;
    
    memset(rx_buffer, 0, sizeof(rx_buffer));
    
    while (HAL_GetTick() - start < timeout_ms) {
        if (HAL_UART_Receive(&huart2, &rx_buffer[index], 1, 100) == HAL_OK) {
            if (index < sizeof(rx_buffer) - 1) {
                index++;
            }
            rx_buffer[index] = '\0';
            if (strstr((char*)rx_buffer, expected) != NULL) {
                return 1;
            }
        }
    }
    return 0;
}

// 硬复位 ESP8266
void ESP8266_HardReset(void)
{
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, GPIO_PIN_RESET);
    HAL_Delay(500);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, GPIO_PIN_SET);
    HAL_Delay(2000);
    
    uint8_t junk[256];
    for (int i = 0; i < 100; i++) {
        if (HAL_UART_Receive(&huart2, junk, 1, 10) != HAL_OK) break;
    }
}

// ESP8266 初始化
uint8_t ESP8266_Init(void)
{
    // 硬复位
    ESP8266_HardReset();
    
    // 测试 AT 指令
    for (int i = 0; i < 3; i++) {
        ESP8266_SendCmd("AT");
        if (ESP8266_WaitResponse("OK", 2000)) {
            break;
        }
        if (i == 2) return 1;
        HAL_Delay(1000);
    }
    
    // 关闭回显
    ESP8266_SendCmd("ATE0");
    HAL_Delay(500);
    
    // 设置 WiFi 模式为 Station 模式
    ESP8266_SendCmd("AT+CWMODE=1");
    if (!ESP8266_WaitResponse("OK", 2000)) {
        return 1;
    }
    
    return 0;
}

// 连接 WiFi,因为连接wifi热点信号会比较弱，要多次尝试连接，这里就需要一直尝试连接直到连接成功为止
uint8_t ESP8266_ConnectWiFi(const char* ssid, const char* password)
{
    char cmd[128];
    uint8_t retry_count = 0;
    
    // 先退出当前 WiFi 连接
    ESP8266_SendCmd("AT+CWQAP");
    HAL_Delay(500);
	
		// 清空串口缓冲区
    uint8_t junk;
    while (HAL_UART_Receive(&huart2, &junk, 1, 10) == HAL_OK);// 丢弃所有残留数据
		
    sprintf(cmd, "AT+CWJAP=\"%s\",\"%s\"", ssid, password);
    
    // 无限循环，直到连接成功
    while (1) {
        retry_count++;
        UsartPrintf(&huart1, "WiFi connect attempt %d...\r\n", retry_count);
        
			  // 每 5 次失败后硬复位模块
        if (retry_count % 5 == 0) {
            UsartPrintf(&huart1, "Multiple failures, hard resetting...\r\n");
						ESP8266_HardReset();
            ESP8266_Init();
						//硬复位后清空缓冲区
            while (HAL_UART_Receive(&huart2, &junk, 1, 10) == HAL_OK);
        }
			
        ESP8266_SendCmd(cmd);
        
        // 等待响应，最多 20 秒
        uint32_t start = HAL_GetTick();
        uint8_t got_ip = 0;
        
        while (HAL_GetTick() - start < 20000) {
            if (ESP8266_WaitResponse("GOT IP", 500)) {
                got_ip = 1;
                break;
            }
            // 检查是否明确失败
            if (ESP8266_WaitResponse("FAIL", 500)) {
                break;
            }
        }
        
        if (got_ip) {
            // 额外验证：查询 IP
            ESP8266_SendCmd("AT+CIFSR");
            HAL_Delay(500);
            UsartPrintf(&huart1, "WiFi Connected! (attempt %d)\r\n", retry_count);
            return 0;
        }
        
        // 连接失败，等待 3 秒后重试
				
				//发送失败后清空缓冲区
        while (HAL_UART_Receive(&huart2, &junk, 1, 10) == HAL_OK);
				
        UsartPrintf(&huart1, "WiFi connect failed, retrying in 3s...\r\n");
        HAL_Delay(3000);
    }
}

// 连接 TCP 服务器
uint8_t ESP8266_ConnectServer(const char* server_ip, uint16_t port)
{
    char cmd[64];
    sprintf(cmd, "AT+CIPSTART=\"TCP\",\"%s\",%d", server_ip, port);
    
    ESP8266_SendCmd(cmd);
    return ESP8266_WaitResponse("CONNECT", 5000);
}

// 发送 HTTP POST 请求
uint8_t ESP8266_SendHttpPost(const char* server_ip, uint16_t port, const char* json_data)
{
    char cmd[32];
    uint16_t content_length = strlen(json_data);
    
    // 先连接服务器
    if (!ESP8266_ConnectServer(server_ip, port)) {
        return 1;
    }
    
    // 构建 HTTP 请求报文
    char http_request[512];
    int len = snprintf(http_request, sizeof(http_request),
        "POST /api/upload HTTP/1.1\r\n"
        "Host: %s:%d\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: %d\r\n"
        "\r\n"
        "%s",
        server_ip, port, content_length, json_data);
    
    // 发送 CIPSEND 指令
    sprintf(cmd, "AT+CIPSEND=%d", len);
    ESP8266_SendCmd(cmd);
    
    // 等待 '>' 提示符
    if (!ESP8266_WaitResponse(">", 2000)) {
        return 1;
    }
    
    // 发送 HTTP 请求
    HAL_UART_Transmit(&huart2, (uint8_t*)http_request, len, 5000);
    
    // 等待服务器响应
    if (ESP8266_WaitResponse("200 OK", 5000)) {
        return 0;
    }
    return 1;
}

// 检查 WiFi 是否还在线
uint8_t ESP8266_CheckWiFiAlive(void)
{
    // 直接发送查询命令，不等待响应（让后续发送时自然处理）
    ESP8266_SendCmd("AT+CIPSTATUS");
    
    // 返回 1 假设在线，让实际发送时失败再处理
    return 1;  // 简化处理，实际靠发送结果决定
}

// 确保 WiFi 连接（如果不连则重连）
uint8_t ESP8266_EnsureWiFi(const char* ssid, const char* password)
{
    // 简单尝试一次连接，失败则硬复位重连
    if (ESP8266_ConnectWiFi(ssid, password) == 0) {
        return 0;
    }
    
    UsartPrintf(&huart1, "WiFi dead, hard reset...\r\n");
    ESP8266_HardReset();
    ESP8266_Init();
    
    while (ESP8266_ConnectWiFi(ssid, password) != 0) {
        UsartPrintf(&huart1, "Reconnect failed, retrying...\r\n");
        HAL_Delay(3000);
    }
    return 0;
}



