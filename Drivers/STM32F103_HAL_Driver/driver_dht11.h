#ifndef _DRIVER_DHT11_H
#define _DRIVER_DHT11_H

extern double temperature;
extern double humidity;
void DHT11_Init(void);
int DHT11_Read(double *hum, double *temp);
void DHT11_Get(void);


#endif

