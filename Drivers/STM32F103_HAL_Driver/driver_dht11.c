#include "driver_dht11.h"
#include "driver_timer.h"
#include "stm32f1xx_hal.h"
#include "driver_oled.h"

double temperature=37;
double humidity=55;

/* 控制GPIO读取DHT11的数据 
 * 1. 主机发出至少18MS的低脉冲: start信号
 * 2. start信号变为高, 20-40us之后, dht11会拉低总线维持80us
      然后拉高80us: 回应信号
 * 3. 之后就是数据, 逐位发送
 *    bit0 : 50us低脉冲, 26-28us高脉冲
 *    bit1 : 50us低脉冲, 70us高脉冲
 * 4. 数据有40bit: 8bit湿度整数数据+8bit湿度小数数据
                   +8bit温度整数数据+8bit温度小数数据
                   +8bit校验和
 */

/**********************************************************************
 * 函数名称： DHT11_PinCfgAsInput
 * 功能描述： 把DHT11的数据引脚配置为输入
 * 输入参数： 无
 * 输出参数： 无
 * 返 回 值： 无
 ***********************************************************************/
static void DHT11_PinCfgAsInput(void)
{
    /* 对于STM32F1, 已经把DHT11的引脚配置为"open drain, pull-up" 
	* 让它输出1就不会驱动这个引脚, 并且可以读入引脚状态
     */
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_1, GPIO_PIN_SET);
}

/**********************************************************************
 * 函数名称： DHT11_PinSet
 * 功能描述： 设置DHT11的数据引脚的输出值
 * 输入参数： val - 输出电平
 * 输出参数： 无
 * 返 回 值： 无
 ***********************************************************************/
static void DHT11_PinSet(int val)
{
	if (val)
		HAL_GPIO_WritePin(GPIOA, GPIO_PIN_1, GPIO_PIN_SET);
	else
		HAL_GPIO_WritePin(GPIOA, GPIO_PIN_1, GPIO_PIN_RESET);
}

/**********************************************************************
 * 函数名称： DHT11_PinRead
 * 功能描述： 读取DHT11的数据引脚
 * 输入参数： 无
 * 输出参数： 无
 * 返 回 值： 1-高电平, 0-低电平
 ***********************************************************************/
static int DHT11_PinRead(void)
{
    if (GPIO_PIN_SET == HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_1))
		return 1;
	else
		return 0;
}


/* 再来实现DHT11的读操作 */
/**********************************************************************
 * 函数名称： DHT11_Start
 * 功能描述： 给DHT11发出启动信号 
 * 输入参数： 无
 * 输出参数： 无
 * 返 回 值： 无
 ***********************************************************************/
static void DHT11_Start(void)
{
	DHT11_PinSet(0);
	mdelay(20);
	DHT11_PinCfgAsInput();
}


/**********************************************************************
 * 函数名称： DHT11_Wait_Ack
 * 功能描述： 等待DHT11的回应信号
 * 输入参数： 无
 * 输出参数： 无
 * 返 回 值： 1-无响应, 0-有响应
 ***********************************************************************/
static int DHT11_Wait_Ack(void)
{
	udelay(60);
	return DHT11_PinRead();
}

/**********************************************************************
 * 函数名称： DHT11_WaitFor_Val
 * 功能描述： 在指定时间内等待数据引脚变为某个值
 * 输入参数： val - 期待数据引脚变为这个值
 *            timeout_us - 超时时间(单位us)
 * 输出参数： 无
 * 返 回 值： 0-成功, (-1) - 失败
 ***********************************************************************/
static int DHT11_WaitFor_Val(int val, int timeout_us)
{
	while (timeout_us--)
	{
		if (DHT11_PinRead() == val)
			return 0; /* ok */
		udelay(1);
	}
	return -1; /* err */
}

/**********************************************************************
 * 函数名称： DHT11_ReadByte
 * 功能描述： 读取DH11 1byte数据
 * 输入参数： 无
 * 输出参数： 无
 * 返 回 值： 数据
 ***********************************************************************/
static int DHT11_ReadByte(void)
{
	int i;
	int data = 0;
	
	for (i = 0; i < 8; i++)
	{
		if (DHT11_WaitFor_Val(1, 1000))
		{
			//printf("dht11 wait for high data err!\n\r");
			return -1;
		}
		udelay(40);
		data <<= 1;
		if (DHT11_PinRead() == 1)
			data |= 1;
		
		if (DHT11_WaitFor_Val(0, 1000))
		{
			//printf("dht11 wait for low data err!\n\r");
			return -1;
		}
	}
	
	return data;
}



/* 公开的函数 */

/**********************************************************************
 * 函数名称： DHT11_Init
 * 功能描述： DHT11的初始化函数
 * 输入参数： 无
 * 输出参数： 无
 * 返 回 值： 无
 ***********************************************************************/
void DHT11_Init(void)
{
	DHT11_PinSet(1);
	//mdelay(2000);
}


/**********************************************************************
 * 函数名称： DHT11_Read
 * 功能描述： 读取DHT11的温度/湿度
 * 输入参数： 无
 * 输出参数： hum  - 用于保存湿度值
 *            temp - 用于保存温度值
 * 返 回 值： 0 - 成功, (-1) - 失败
 ***********************************************************************/
int DHT11_Read(double *hum, double *temp)
{
	unsigned char hum_m, hum_n;
	unsigned char temp_m, temp_n;
	unsigned char check;	
	
	DHT11_Start();
	
	if (0 != DHT11_Wait_Ack())
	{
		//printf("dht11 not ack, err!\n\r");
		return -1;
	}

	if (0 != DHT11_WaitFor_Val(1, 1000))  /* 等待ACK变为高电平, 超时时间是1000us */
	{
		//printf("dht11 wait for ack high err!\n\r");
		return -1;
	}

	if (0 != DHT11_WaitFor_Val(0, 1000))  /* 数据阶段: 等待低电平, 超时时间是1000us */
	{
		//printf("dht11 wait for data low err!\n\r");
		return -1;
	}

	hum_m  = DHT11_ReadByte();
	hum_n  = DHT11_ReadByte();
	temp_m = DHT11_ReadByte();
	temp_n = DHT11_ReadByte();
	check  = DHT11_ReadByte();

	DHT11_PinSet(1);

	if (hum_m + hum_n + temp_m + temp_n == check)
	{
        *hum  = (float)hum_m + (float)hum_n / 10.0f;   // 小数计算
        *temp = (float)temp_m + (float)temp_n / 10.0f;
		return 0;
	}
	else
	{
		return -1;
	}
}


/**********************************************************************
 * 函数名称： DHT11_Get
 * 功能描述： DHT11温湿度获取
 * 输入参数： 无
 * 输出参数： 无
 *            无
 * 返 回 值： 无
 ***********************************************************************/
void DHT11_Get(void)
{
		static double last_valid_humidity = 55;
    static double last_valid_temperature = 37;
    if (DHT11_Read(&humidity, &temperature) == 0)
    {
        // 读取成功，更新有效值
        last_valid_humidity = humidity;
        last_valid_temperature = temperature;
    }
    else
    {
        // 读取失败，使用上一次有效值
        humidity = last_valid_humidity;
        temperature = last_valid_temperature;
        DHT11_Init();
    }
}


