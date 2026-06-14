#ifndef _DRIVER_UART_H
#define _DRIVER_UART_H
#include "stm32f1xx_hal.h"
void Usart_SendString(UART_HandleTypeDef  *USARTx, unsigned char *str, unsigned short len);
void UsartPrintf(UART_HandleTypeDef *USARTx, char *fmt,...);
#endif /* _DRIVER_UART_H */

