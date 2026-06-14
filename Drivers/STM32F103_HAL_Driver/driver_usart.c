#include "stm32f1xx_hal.h"
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include "driver_usart.h"

#define DEBUG_UART_TIMEOUT 500

// 串口2接收缓冲
#define UART2_RX_BUF_SIZE 512
uint8_t uart2_rx_buffer[UART2_RX_BUF_SIZE];
uint16_t uart2_rx_index = 0;
/*
************************************************************
* 全局串口句柄（USART2）
************************************************************
*/
extern UART_HandleTypeDef huart2;
extern UART_HandleTypeDef huart1;
/*
************************************************************
* printf 重定向 → 固定输出到 USART1
************************************************************
*/

int fputc(int c, FILE *f)
{
	(void)f;
	HAL_UART_Transmit(&huart1, (const uint8_t *)&c, 1, DEBUG_UART_TIMEOUT);
	return c;
}

int fgetc(FILE *f)
{
	uint8_t ch = 0;
	(void)f;

	__HAL_UART_CLEAR_OREFLAG(&huart1);
	HAL_UART_Receive(&huart1, &ch, 1, HAL_MAX_DELAY);
	HAL_UART_Transmit(&huart1, &ch, 1, DEBUG_UART_TIMEOUT);
	return ch;
}

/*
************************************************************
*	函数名称：	Usart_SendString
*
*	函数功能：	串口数据发送
*
*	入口参数：	USARTx：串口组
*				str：要发送的数据
*				len：数据长度
*
*	返回参数：	无
*
*	说明：		
************************************************************
*/
void Usart_SendString(UART_HandleTypeDef  *USARTx, unsigned char *str, unsigned short len)
{
	unsigned short count = 0;
	
	for(; count < len; count++)
	{
		HAL_UART_Transmit(USARTx,str++,1,HAL_MAX_DELAY);
	}
}

/*
************************************************************
*	函数名称：	UsartPrintf
*
*	函数功能：	格式化打印
*
*	入口参数：	USARTx：串口组
*				fmt：不定长参
*
*	返回参数：	无
*
*	说明：		
************************************************************
*/
void UsartPrintf(UART_HandleTypeDef *USARTx, char *fmt,...)
{
    // 1. 定义足够大的缓冲区，防止溢出
    char buf[256];
    va_list ap;
    // 2. 安全格式化，强制检查缓冲区大小
    va_start(ap, fmt);
    int len = vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);

    // 3. 格式化失败直接返回，避免发送垃圾数据
    if(len <= 0 || len >= sizeof(buf)) return;

    // 4. 一次性发送整帧字符串，绝对不逐字节发送
    HAL_UART_Transmit(USARTx, (uint8_t*)buf, len, 100);
}

// 启动串口2中断接收
void UART2_StartReceive(void)
{
    HAL_UART_Receive_IT(&huart2, &uart2_rx_buffer[uart2_rx_index], 1);
}


