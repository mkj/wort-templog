/* Name: main.c
 * Author: <insert your name here>
 * Copyright: <insert your copyright message here>
 * License: <insert your license reference here>
 */

#include <avr/io.h>
#include <stdio.h>
#include <string.h>
#include <util/crc16.h>

// configuration params
// - measurement interval
// - transmit interval
// - bluetooth params
// - number of sensors (and range?)

static int uart_putchar(char c, FILE *stream);
static FILE mystdout = FDEV_SETUP_STREAM(uart_putchar, NULL,
        _FDEV_SETUP_WRITE);

static uint8_t n_measurements;
static uint8_t measurements[500];

static uint8_t readpos;
static char readbuf[30];

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
        crc = _crc_ccitt_updatec(crc, measurements[i]);
    }
        printf("CRC : %d\n", i, measurements[i]);
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

ISR(UART_RX_vect)
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

int main(void)
{
    uart_init(9600);

    fprintf(&mystdout, "hello %d\n", 12);

    // get current time

    for(;;){
        /* insert your main loop code here */
    }
    return 0;   /* never reached */
}
