/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "i2c.h"
#include "tim.h"
#include "usart.h"
#include "gpio.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include "driver_oled.h"
#include "driver_dht11.h"
#include "driver_timer.h"
#include "driver_usart.h"
#include "driver_wifi.h"
#include <stdio.h>
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */
extern uint8_t uart2_rx_byte;
/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/

/* USER CODE BEGIN PV */

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
/* USER CODE BEGIN PFP */

/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */
// WiFi 配置
#define WIFI_SSID     "Qingci"//WiFi名称
#define WIFI_PASSWORD "Msq528432"//WiFi密码
#define SERVER_IP     "10.115.93.238"  // 电脑 IP
#define SERVER_PORT   5000
		
#define COLLECT_INTERVAL_MS  300000    // 采集间隔5min
#define KEEPALIVE_INTERVAL_MS  60000  // 60秒保活一次

/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{

  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_I2C1_Init();
  MX_I2C2_Init();
  MX_TIM1_Init();
  MX_USART2_UART_Init();
  MX_USART1_UART_Init();
  /* USER CODE BEGIN 2 */
	Timer_Init();
	DHT11_Init();
	OLED_Init();
	OLED_Clear();
	
	UsartPrintf(&huart1, "System Starting...\r\n");
    
    // 初始化 ESP8266
    UsartPrintf(&huart1, "Init ESP8266...\r\n");
    while (ESP8266_Init() != 0) {
        UsartPrintf(&huart1, "ESP8266 Init Failed, retrying...\r\n");
        HAL_Delay(2000);
    }
    UsartPrintf(&huart1, "ESP8266 OK\r\n");
    
    // 连接 WiFi - 一直重试直到成功
    UsartPrintf(&huart1, "Connecting WiFi...\r\n");
    OLED_PrintString(0, 6, "WifiConn");
    
    while (ESP8266_ConnectWiFi(WIFI_SSID, WIFI_PASSWORD) != 0) {
        UsartPrintf(&huart1, "WiFi Connect Failed, retrying...\r\n");
        OLED_PrintString(0, 6, "WifiRetry");
        HAL_Delay(3000);
    }
    
    UsartPrintf(&huart1, "WiFi Connected!\r\n");
    OLED_PrintString(0, 6, "WiFi OK ");
    
    // 记录上次采集时间和上次保活检查时间
    uint32_t last_collect_time = HAL_GetTick();
    uint32_t last_keepalive_time = HAL_GetTick();
  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
		
while (1)
{
    uint32_t now = HAL_GetTick();

    // ========== 1. 定时采集上传 ==========
    if (now - last_collect_time >= COLLECT_INTERVAL_MS)
    {
        last_collect_time = now;

        // 读温湿度
        DHT11_Get();

        // OLED显示
        OLED_PrintString(0, 0, "Temp:");
        OLED_PrintFloatVal(7, 0, temperature, 2);
        OLED_PrintString(12, 0, "C");

        OLED_PrintString(0, 2, "Humi:");
        OLED_PrintFloatVal(7, 2, humidity, 2);
        OLED_PrintString(12, 2, "%");

        OLED_PrintString(0, 4, "            ");

        UsartPrintf(&huart1, "\r\n=== Collect & Upload ===\r\n");
        UsartPrintf(&huart1, "Temp: %.2f, Humi: %.2f\r\n", temperature, humidity);

        // 构建JSON
        char json_data[128];
        snprintf(json_data, sizeof(json_data),
            "{\"device_id\":1,\"temperature\":%.2f,\"humidity\":%.2f}",
            temperature, humidity);

        UsartPrintf(&huart1, "Sending: %s\r\n", json_data);

        // 发送数据
        uint8_t send_result = ESP8266_SendHttpPost(SERVER_IP, SERVER_PORT, json_data);
        if (send_result == 0)
        {
            UsartPrintf(&huart1, "Send OK\r\n");
            OLED_PrintString(0, 6, "WiFi OK  Send OK");
        }
        else
        {
            UsartPrintf(&huart1, "Send Failed, reconnect TCP only...\r\n");
            OLED_PrintString(0, 6, "TCP Reconnect");

						// 关闭TCP
						ESP8266_SendCmd("AT+CIPCLOSE");
						HAL_Delay(500);
						
					  // 重置保活计时器，避免重连过程中又发保活
						last_keepalive_time = HAL_GetTick();
					
						// 重连WiFi
						ESP8266_ConnectWiFi(WIFI_SSID, WIFI_PASSWORD);
        }
    }
    else
    {
        // 倒计时显示
        uint32_t remaining_ms = COLLECT_INTERVAL_MS - (now - last_collect_time);
        uint32_t remaining_sec = remaining_ms / 1000;
        uint32_t remaining_min = remaining_sec / 60;
        uint32_t remaining_sec_mod = remaining_sec % 60;

        char countdown_str[20];
        sprintf(countdown_str, "Next:%02lu:%02lu",
            (unsigned long)remaining_min,
            (unsigned long)remaining_sec_mod);
        OLED_PrintString(0, 4, countdown_str);
						
				// 在 else 分支中，先检查 WiFi 是否还在线
				if (now - last_keepalive_time >= KEEPALIVE_INTERVAL_MS) {
						// 只检查 WiFi 状态，不发保活
						ESP8266_SendCmd("AT+CIPSTATUS");
						// 简单判断：如果不响应，说明 WiFi 已断
						if (!ESP8266_WaitResponse("STATUS", 500)) {
								// WiFi 已断，不继续发保活
						} else {
								// WiFi 正常，发保活
								UsartPrintf(&huart1, "Keepalive...\r\n");
								ESP8266_SendCmd("AT");
						}
						last_keepalive_time = now;// 重置计时器，避免频繁检查
				}
    }

    HAL_Delay(1000);
}
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
		
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
  RCC_OscInitStruct.HSEState = RCC_HSE_ON;
  RCC_OscInitStruct.HSEPredivValue = RCC_HSE_PREDIV_DIV1;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
  RCC_OscInitStruct.PLL.PLLMUL = RCC_PLL_MUL9;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK)
  {
    Error_Handler();
  }
}

/* USER CODE BEGIN 4 */

/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}
#ifdef USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
