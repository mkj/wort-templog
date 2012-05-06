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

// configuration params
// - measurement interval
// - transmit interval
// - bluetooth params
// - number of sensors (and range?)

// 1 second. we have 1024 prescaler, 32768 crystal.
static const uint8_t CNT2_COMPARE = 32;
static const int SECONDS_WAKE = 60;

static int uart_putchar(char c, FILE *stream);
static FILE mystdout = FDEV_SETUP_STREAM(uart_putchar, NULL,
        _FDEV_SETUP_WRITE);

static uint8_t n_measurements;
static uint8_t measurements[500];

static uint8_t need_measurement;

static uint8_t readpos;
static char readbuf[30];

static uint8_t sec_count;

static void 
uart_init(unsigned int baud)
{
    // baud rate
    UBRRH = (unsigned char)(baud >> 8);
    UBRRL = (unsigned char)baud;
    UCSRB = (1<<RXEN)|(1<<TXEN);
    //8N1
    UCSRC = (1<<URSEL)|(3<<UCSZ0);
}

static int 
uart_putchar(char c, FILE *stream)
{
    // XXX should sleep in the loop for power.
    loop_until_bit_is_set(UCSRA, UDRE);
    UDR = c;
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

ISR(USART_RXC_vect)
{
    char c = UDR;
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

ISR(TIMER2_COMP_vect)
{
    sec_count ++;
    if (sec_count == SECONDS_WAKE)
    {
        sec_count = 0;
        need_measurement = 1;
    }
}

static void
deep_sleep()
{
    // p119 of manual
    OCR2 = CNT2_COMPARE;
    loop_until_bit_is_clear(ASSR, OCR2UB);

    set_sleep_mode(SLEEP_MODE_PWR_SAVE);
    sleep_mode();
}

static void
do_measurement()
{
    need_measurement = 0;
}

int main(void)
{
    uart_init(9600);

    fprintf(&mystdout, "hello %d\n", 12);

    // set up counter2. 
    // COM21 COM20 Set OC2 on Compare Match (p116)
    // WGM21 Clear counter on compare
    // CS22 CS21 CS20  clk/1024
    TCCR2 = _BV(COM21) | _BV(COM20) | _BV(WGM21) | _BV(CS22) | _BV(CS21) | _BV(CS20);
    // set async mode
    ASSR |= _BV(AS2);

    for(;;){
        /* insert your main loop code here */
        if (need_measurement)
        {
            do_measurement();
        }
    }
    return 0;   /* never reached */
}
