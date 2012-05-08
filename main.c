/* Name: main.c
 * Author: <insert your name here>
 * Copyright: <insert your copyright message here>
 * License: <insert your license reference here>
 */

#include <stdio.h>
#include <string.h>
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/sleep.h>
#include <util/crc16.h>

#include "integer.h"

// configuration params
// - measurement interval
// - transmit interval
// - bluetooth params
// - number of sensors (and range?)

// 1 second. we have 1024 prescaler, 32768 crystal.
#define SLEEP_COMPARE 32
#define MEASURE_WAKE 60

#define COMMS_WAKE 3600

#define BAUD 9600
#define UBRR ((F_CPU)/16/(BAUD)-1)

static int uart_putchar(char c, FILE *stream);
static FILE mystdout = FDEV_SETUP_STREAM(uart_putchar, NULL,
        _FDEV_SETUP_WRITE);

static uint8_t n_measurements;
static uint8_t measurements[500];

// boolean flags
static uint8_t need_measurement;
static uint8_t need_comms;
static uint8_t comms_done;

static uint8_t readpos;
static char readbuf[30];

static uint8_t sec_count;
static uint16_t bt_count;

static void deep_sleep();

static void 
uart_init(unsigned int ubrr)
{
    // baud rate
    UBRR0H = (unsigned char)(ubrr >> 8);
    UBRR0L = (unsigned char)ubrr;
    UCSR0B = (1<<RXEN0)|(1<<TXEN0);
    //8N1
    UCSR0C = (1<<UMSEL00)|(3<<UCSZ00);
}

static int 
uart_putchar(char c, FILE *stream)
{
    // XXX should sleep in the loop for power.
    loop_until_bit_is_set(UCSR0A, UDRE0);
    UDR0 = c;
    return 0;
}

static void
cmd_fetch()
{
    uint16_t crc = 0;
    int i;
    printf("%d measurements\n", n_measurements);
    for (i = 0; i < n_measurements; i++)
    {
        printf("%3d : %d\n", i, measurements[i]);
        crc = _crc_ccitt_update(crc, measurements[i]);
    }
    printf("CRC : %d\n", crc);
}

static void
cmd_clear()
{
}

static void
cmd_btoff()
{
	comms_done = 1;
}

static void
read_handler()
{
    if (strcmp(readbuf, "fetch") == 0)
    {
        cmd_fetch();
    }
    else if (strcmp(readbuf, "clear") == 0)
    {
        cmd_clear();
    }
    else if (strcmp(readbuf, "btoff") == 0)
    {
        cmd_btoff();
    }
    else
    {
        printf("Bad command\n");
    }
}

ISR(USART_RX_vect)
{
    char c = UDR0;
    if (c == '\n')
    {
        readbuf[readpos] = '\0';
        read_handler();
        readpos = 0;
    }
    else
    {
        readbuf[readpos] = c;
        readpos++;
        if (readpos >= sizeof(readbuf))
        {
            readpos = 0;
        }
    }
}

ISR(TIMER2_COMPA_vect)
{
    measure_count ++;
	comms_count ++;
    if (measure_count == MEASURE_WAKE)
    {
        measure_count = 0;
        need_measurement = 1;
    }

	if (comms_count == COMMS_WAKE)
	{
		comms_count = 0;
		need_comms = 1;
	}
}

DWORD get_fattime (void)
{
    return 0;
}

static void
deep_sleep()
{
    // p119 of manual
    OCR2A = SLEEP_COMPARE;
    loop_until_bit_is_clear(ASSR, OCR2AUB);

    set_sleep_mode(SLEEP_MODE_PWR_SAVE);
    sleep_mode();
}

static void
idle_sleep()
{
    set_sleep_mode(SLEEP_MODE_IDLE);
    sleep_mode();
}

static void
do_measurement()
{
    need_measurement = 0;
}

static void
do_comms()
{
	need_comms = 0;

	// turn on bluetooth
	// turn on serial (interrupts)
	
	// write sd card here? same 3.3v regulator...
	
	comms_done = 0;
	for (;;)
	{
		if (comms_done)
		{
			break;
		}
		idle_sleep();
	}

	// turn off bluetooth
	// turn off serial (interrupts)
}

int main(void)
{
    uart_init(UBRR);

    fprintf(&mystdout, "hello %d\n", 12);

    // set up counter2. 
    // COM21 COM20 Set OC2 on Compare Match (p116)
    // WGM21 Clear counter on compare
    // CS22 CS21 CS20  clk/1024
    TCCR2A = _BV(COM2A1) | _BV(COM2A0) | _BV(WGM21);
    TCCR2B = _BV(CS22) | _BV(CS21) | _BV(CS20);
    // set async mode
    ASSR |= _BV(AS2);

    for(;;){
        /* insert your main loop code here */
        if (need_measurement)
        {
            do_measurement();
			continue;
        }

        if (need_comms)
        {
            do_comms();
			continue;
        }

		deep_sleep();
    }
    return 0;   /* never reached */
}
