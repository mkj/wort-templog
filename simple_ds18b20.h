#ifndef SIMPLE_DS18B20_H_
#define SIMPLE_DS18B20_H_
#include <stdint.h>

#include "ds18x20.h"

uint8_t simple_ds18b20_start_meas(uint8_t id[]);
void printhex(uint8_t *id, uint8_t n);
void printhex_byte( const unsigned char  b );
uint8_t simple_ds18b20_read_decicelsius( uint8_t id[], int16_t *decicelsius );
uint8_t simple_ds18b20_read_all();

#endif // SIMPLE_DS18B20_H_