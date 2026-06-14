// driver_wifi.h
#ifndef _DRIVER_WIFI_H
#define _DRIVER_WIFI_H

#include "main.h"

void ESP8266_SendCmd(const char* cmd);
uint8_t ESP8266_WaitResponse(const char* expected, uint32_t timeout_ms);
uint8_t ESP8266_Init(void);
uint8_t ESP8266_ConnectWiFi(const char* ssid, const char* password);
uint8_t ESP8266_ConnectServer(const char* server_ip, uint16_t port);
uint8_t ESP8266_SendHttpPost(const char* server_ip, uint16_t port, const char* json_data);
uint8_t ESP8266_CheckWiFiAlive(void);
uint8_t ESP8266_EnsureWiFi(const char* ssid, const char* password);
void ESP8266_HardReset(void);
#endif
