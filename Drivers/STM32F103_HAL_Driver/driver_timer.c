#include "driver_timer.h"
#include "stm32f1xx_hal.h"

extern TIM_HandleTypeDef htim1;

// 初始化TIM1
void Timer_Init(void)
{
    // CubeMX已经生成了MX_TIM1_Init()，在main.c中调用即可
    HAL_TIM_Base_Start(&htim1);  // 启动定时器
}

/**********************************************************************
 * 函数名称： udelay
 * 功能描述： us级别的延时函数（使用TIM1）
 * 输入参数： us - 延时多少us (最大65535us ≈ 65ms)
 * 输出参数： 无
 * 返 回 值： 无
 ***********************************************************************/
void udelay(uint32_t us)
{
    if (us == 0) return;
    if (us > 65535) us = 65535;  // 限制最大值
    
    TIM_HandleTypeDef *htim = &htim1;
    uint32_t start = __HAL_TIM_GET_COUNTER(htim);
    uint32_t target = us;  // 因为定时器1us计数一次，所以目标值就是us
    uint32_t current;
    uint32_t elapsed;
    uint32_t reload = __HAL_TIM_GET_AUTORELOAD(htim);
    
    while (1) {
        current = __HAL_TIM_GET_COUNTER(htim);
        
        // 计算经过的时间（处理计数器溢出）
        if (current >= start) {
            elapsed = current - start;
        } else {
            elapsed = (reload - start) + current + 1;
        }
        
        if (elapsed >= target) {
            break;
        }
    }
}

/**********************************************************************
 * 函数名称： mdelay
 * 功能描述： ms级别的延时函数
 * 输入参数： ms - 延时多少ms
 * 输出参数： 无
 * 返 回 值： 无
 ***********************************************************************/
void mdelay(uint32_t ms)
{
    for (uint32_t i = 0; i < ms; i++) {
        udelay(1000);
    }
}

/**********************************************************************
 * 函数名称： system_get_ns
 * 功能描述： 获得系统时间(单位ns)
 * 输入参数： 无
 * 输出参数： 无
 * 返 回 值： 系统时间(单位ns)
 ***********************************************************************/
uint64_t system_get_ns(void)
{
    extern TIM_HandleTypeDef htim1;
    TIM_HandleTypeDef *hHalTim = &htim1;
    
    uint64_t ns = HAL_GetTick();  // 毫秒部分
    uint32_t cnt = __HAL_TIM_GET_COUNTER(hHalTim);
    uint32_t reload = __HAL_TIM_GET_AUTORELOAD(hHalTim);
    
    // 转换：1ms = 1,000,000ns
    // cnt/reload 是微秒的小数部分
    ns = ns * 1000000 + (cnt * 1000000 / reload);
    return ns;
}
