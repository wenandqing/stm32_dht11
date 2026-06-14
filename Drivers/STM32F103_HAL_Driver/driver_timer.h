
#ifndef _DRIVER_TIMER_H
#define _DRIVER_TIMER_H

#include <stdint.h>

void Timer_Init(void);
void udelay(uint32_t  us);
void mdelay(uint32_t  ms);
uint64_t system_get_ns(void);


#endif /* _DRIVER_TIMER_H */

