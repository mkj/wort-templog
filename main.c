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
#include <util/delay.h>
#include <avr/pgmspace.h>
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
#define UBRR ((F_CPU)/8/(BAUD)-1)

#define PORT_LED PORTC
#define DDR_LED DDRC
#define PIN_LED PC4

#define NUM_MEASUREMENTS 300

static int uart_putchar(char c, FILE *stream);
static FILE mystdout = FDEV_SETUP_STREAM(uart_putchar, NULL,
        _FDEV_SETUP_WRITE);

static uint8_t n_measurements = 0;
// stored as 1/5 degree above 0
static uint8_t measurements[NUM_MEASUREMENTS];
static uint8_t internal_measurements[NUM_MEASUREMENTS];

// boolean flags
static uint8_t need_measurement = 0;
static uint8_t need_comms = 0;
static uint8_t comms_done = 0;

static uint8_t readpos = 0;
static char readbuf[30];

static uint8_t measure_count = 0;
static uint16_t comms_count = 0;

static void deep_sleep();

static void 
uart_on()
{
    // baud rate
    UBRR0H = (unsigned char)(UBRR >> 8);
    UBRR0L = (unsigned char)UBRR;
    // set 2x clock, improves accuracy of UBRR
    UCSR0A |= _BV(U2X0);
    UCSR0B = _BV(RXCIE0) | _BV(RXEN0) | _BV(TXEN0);
    //8N1
    UCSR0C = _BV(UCSZ01) | _BV(UCSZ00);

    // Power reduction register
    //PRR &= ~_BV(PRUSART0);
}

static void
uart_test()
{

    UDR0 = 'n';
    _delay_ms(50);
    UDR0 = 'f';
    _delay_ms(50);
    while ( !( UCSR0A & (1<<UDRE0)) );
    UDR0 = 'x';
    loop_until_bit_is_set(UCSR0A, UDRE0);
    UDR0 = 'a';
    loop_until_bit_is_set(UCSR0A, UDRE0);
    UDR0 = 'b';
    loop_until_bit_is_set(UCSR0A, UDRE0);
    UDR0 = 'c';
    loop_until_bit_is_set(UCSR0A, UDRE0);
    UDR0 = '\n';
}

static void 
uart_off()
{
    // Turn of interrupts and disable tx/rx
    UCSR0B = 0;

    // Power reduction register
    PRR |= _BV(PRUSART0);
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
    printf_P(PSTR("%d measurements\n"), n_measurements);
    for (i = 0; i < n_measurements; i++)
    {
        printf_P(PSTR("%3d : %d\n"), i, measurements[i]);
        crc = _crc_ccitt_update(crc, measurements[i]);
    }
    printf_P(PSTR("CRC : %d\n"), crc);
}

static void
cmd_clear()
{
    n_measurements = 0;
    printf_P(PSTR("Cleared\n"));
}

static void
cmd_btoff()
{
    printf_P(PSTR("Turning off\n"));
    _delay_ms(50);
	comms_done = 1;
}

static void
read_handler()
{
    if (strcmp_P(readbuf, PSTR("fetch")) == 0)
    {
        cmd_fetch();
    }
    else if (strcmp_P(readbuf, PSTR("clear")) == 0)
    {
        cmd_clear();
    }
    else if (strcmp_P(readbuf, PSTR("btoff")) == 0)
    {
        cmd_btoff();
    }
    else
    {
        printf_P(PSTR("Bad command\n"));
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

    PORT_LED ^= _BV(PIN_LED);
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
do_adc_335()
{
    PRR &= ~_BV(PRADC);

    ADMUX = _BV(ADLAR);

    // ADPS2 = /16 prescaler, 62khz at 1mhz clock
    ADCSRA = _BV(ADEN) | _BV(ADPS2);
    
    // measure value
    ADCSRA |= _BV(ADSC);
    loop_until_bit_is_clear(ADCSRA, ADSC);
    uint8_t low = ADCL;
    uint8_t high = ADCH;
    uint16_t f_measure = low + (high << 8);

    // set to measure 1.1 reference
    ADMUX = _BV(ADLAR) | _BV(MUX3) | _BV(MUX2) | _BV(MUX1);
    ADCSRA |= _BV(ADSC);
    loop_until_bit_is_clear(ADCSRA, ADSC);
    uint8_t low_11 = ADCL;
    uint8_t high_11 = ADCH;
    uint16_t f_11 = low_11 + (high_11 << 8);

    float res_volts = 1.1 * f_measure / f_11;

    // 10mV/degree
    // scale to 1/5 degree units above 0C
    int temp = (res_volts - 2.73) * 500;
    measurements[n_measurements] = temp;
    // XXX something if it hits the limit

    // measure AVR internal temperature against 1.1 ref.
    ADMUX = _BV(ADLAR) | _BV(MUX3) | _BV(REFS1) | _BV(REFS0);
    ADCSRA |= _BV(ADSC);
    loop_until_bit_is_clear(ADCSRA, ADSC);
    uint16_t res_internal = ADCL;
    res_internal |= ADCH << 8;

    float internal_volts = res_internal * (1.1 / 1024.0);

    // 1mV/degree
    int internal_temp = (internal_volts - 2.73) * 5000;
    internal_measurements[n_measurements] = internal_temp;

    printf_P("measure %d: external %d, internal %d, 1.1 %d\n",
            n_measurements, temp, internal_temp, f_11);

    n_measurements++;
    PRR |= _BV(PRADC);
}

static void
do_measurement()
{
    need_measurement = 0;

    do_adc_335();
}

static void
do_comms()
{
	need_comms = 0;

	// turn on bluetooth
    uart_on();
	
	// write sd card here? same 3.3v regulator...
	
	comms_done = 0;
	for (;;)
	{
		if (comms_done)
		{
			break;
		}

        if (need_measurement)
        {
            do_measurement();
        }

		idle_sleep();
	}

    uart_off();

	// turn off bluetooth
}

static void
blink()
{
    PORT_LED &= ~_BV(PIN_LED);
    _delay_ms(100);
    PORT_LED |= _BV(PIN_LED);
}

static void
long_delay(int ms)
{
    int iter = ms / 100;

    for (int i = 0; i < iter; i++)
    {
        _delay_ms(100);
    }
}

int main(void)
{
    DDR_LED |= _BV(PIN_LED);

    blink();
    long_delay(1000);
    blink();
    long_delay(500);
    stdout = &mystdout;
    uart_on();
    blink();
    long_delay(200);
    blink();
    long_delay(200);
    uart_test();

    PORT_LED &= ~_BV(PIN_LED);
    for (int i = 0; i < 10; i++)
        _delay_ms(100);
    PORT_LED |= _BV(PIN_LED);

    fprintf_P(&mystdout, PSTR("hello %d\n"), 12);
    //uart_off();

    // turn off everything except timer2
    PRR = _BV(PRTWI) | _BV(PRTIM0) | _BV(PRTIM1) | _BV(PRSPI) | _BV(PRUSART0) | _BV(PRADC);

    // set up counter2. 
    // COM21 COM20 Set OC2 on Compare Match (p116)
    // WGM21 Clear counter on compare
    // CS22 CS21 CS20  clk/1024
    TCCR2A = _BV(COM2A1) | _BV(COM2A0) | _BV(WGM21);
    TCCR2B = _BV(CS22) | _BV(CS21) | _BV(CS20);
    // set async mode
    ASSR |= _BV(AS2);

    DDR_LED |= _BV(PIN_LED);
    PORT_LED &= ~_BV(PIN_LED);
    _delay_ms(100);
    PORT_LED |= _BV(PIN_LED);

#ifdef TEST_MODE
    for (;;)
    {
        do_comms()
    }
#else
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
#endif
    return 0;   /* never reached */
}
