#include <stdio.h>
#include <string.h>
#include <stddef.h>
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/sleep.h>
#include <util/delay.h>
#include <avr/pgmspace.h>
#include <avr/eeprom.h>
#include <avr/wdt.h>
#include <util/crc16.h>

// for DWORD of get_fattime()
#include "integer.h"

#include "simple_ds18b20.h"
#include "onewire.h"

// configuration params
// - measurement interval
// - transmit interval
// - bluetooth params
// - number of sensors (and range?)

// 1 second. we have 1024 prescaler, 32768 crystal.
#define SLEEP_COMPARE 32
// limited to uint16_t
#define MEASURE_WAKE 60

#define VALUE_NOSENSOR -9000
#define VALUE_BROKEN -8000

// limited to uint16_t
#define COMMS_WAKE 3600 // XXX testing
// limited to uint8_t
#define WAKE_SECS 60 // XXX testing

#define BAUD 19200
#define UBRR ((F_CPU)/8/(BAUD)-1)

#define PORT_LED PORTC
#define DDR_LED DDRC
#define PIN_LED PC4

#define PORT_SHDN PORTD
#define DDR_SHDN DDRD
#define PIN_SHDN PD7

// limited to uint16_t
// XXX - increasing this to 300 causes strange failures, 
// not sure why
#define NUM_MEASUREMENTS 280
// limited to uint8_t
#define MAX_SENSORS 3

// fixed at 8, have a shorter name
#define ID_LEN OW_ROMCODE_SIZE

// #define HAVE_UART_ECHO

int uart_putchar(char c, FILE *stream);
static void long_delay(int ms);
static void blink();
static void adc_internal(uint16_t *millivolt_vcc, uint16_t *int_temp);

static FILE mystdout = FDEV_SETUP_STREAM(uart_putchar, NULL,
        _FDEV_SETUP_WRITE);

uint16_t crc_out;
static FILE _crc_stdout = FDEV_SETUP_STREAM(uart_putchar, NULL,
        _FDEV_SETUP_WRITE);
// convenience
static FILE *crc_stdout = &_crc_stdout;

static uint16_t n_measurements;
// stored as decidegrees
static int16_t measurements[NUM_MEASUREMENTS][MAX_SENSORS];
static uint32_t first_measurement_clock;
// last_measurement_clock is redundant but checks that we're not missing
// samples
static uint32_t last_measurement_clock;

// boolean flags
static uint8_t need_measurement;
static uint8_t need_comms;
static uint8_t uart_enabled;

// counts down from WAKE_SECS to 0, goes to deep sleep when hits 0
static uint8_t comms_timeout;

static uint8_t readpos;
static char readbuf[30];
static uint8_t have_cmd;

static uint16_t measure_count;
static uint16_t comms_count;

static uint32_t clock_epoch;

// thanks to http://projectgus.com/2010/07/eeprom-access-with-arduino/
#define eeprom_read_to(dst_p, eeprom_field, dst_size) eeprom_read_block((dst_p), (void *)offsetof(struct __eeprom_data, eeprom_field), (dst_size))
#define eeprom_read(dst, eeprom_field) eeprom_read_to((&dst), eeprom_field, sizeof(dst))
#define eeprom_write_from(src_p, eeprom_field, src_size) eeprom_write_block((src_p), (void *)offsetof(struct __eeprom_data, eeprom_field), (src_size))
#define eeprom_write(src, eeprom_field) { eeprom_write_from(&src, eeprom_field, sizeof(src)); }

#define EXPECT_MAGIC 0x67c9

struct __attribute__ ((__packed__)) __eeprom_data {
    uint16_t magic;
    uint8_t n_sensors;
    uint8_t sensor_id[MAX_SENSORS][ID_LEN];
};

#define DEBUG(str) printf_P(PSTR(str))

static void deep_sleep();

// Very first setup
static void
setup_chip()
{
    cli();

    // stop watchdog timer (might have been used to cause a reset)
    wdt_reset();
    MCUSR &= ~_BV(WDRF);
    WDTCSR |= _BV(WDCE) | _BV(WDE);
    WDTCSR = 0;

    // Set clock to 2mhz
    CLKPR = _BV(CLKPCE);
    // divide by 4
    CLKPR = _BV(CLKPS1);

    // enable pullups
    PORTB = 0xff; // XXX change when using SPI
    PORTD = 0xff;
    PORTC = 0xff;

    // 3.3v power for bluetooth and SD
    DDR_LED |= _BV(PIN_LED);
    DDR_SHDN |= _BV(PIN_SHDN);

    // set pullup
    PORTD |= _BV(PD2);
    // INT0 setup
    EICRA = (1<<ISC01); // falling edge - data sheet says it won't work?
    EIMSK = _BV(INT0);

    // comparator disable
    ACSR = _BV(ACD);

    // disable adc pin input buffers
    DIDR0 = 0x3F; // acd0-adc5
    DIDR1 = (1<<AIN1D)|(1<<AIN0D); // ain0/ain1

    sei();
}

static void
set_aux_power(uint8_t on)
{
    if (on)
    {
        PORT_SHDN &= ~_BV(PIN_SHDN);
    }
    else
    {
        PORT_SHDN |= _BV(PIN_SHDN);
    }
}

static void
setup_tick_counter()
{
    // set up counter2. 
    // COM21 COM20 Set OC2 on Compare Match (p116)
    // WGM21 Clear counter on compare
    //TCCR2A = _BV(COM2A1) | _BV(COM2A0) | _BV(WGM21);
    // toggle on match
    TCCR2A = _BV(COM2A0);
    // CS22 CS21 CS20  clk/1024
    TCCR2B = _BV(CS22) | _BV(CS21) | _BV(CS20);
    // set async mode
    ASSR |= _BV(AS2);
    TCNT2 = 0;
    OCR2A = SLEEP_COMPARE;
    // interrupt
    TIMSK2 = _BV(OCIE2A);
}

static void 
uart_on()
{
    // Power reduction register
    PRR &= ~_BV(PRUSART0);
 
    // All of this needs to be done each time after turning off the PRR
    // baud rate
    UBRR0H = (unsigned char)(UBRR >> 8);
    UBRR0L = (unsigned char)UBRR;
    // set 2x clock, improves accuracy of UBRR
    UCSR0A |= _BV(U2X0);
    UCSR0B = _BV(RXCIE0) | _BV(RXEN0) | _BV(TXEN0);
    //8N1
    UCSR0C = _BV(UCSZ01) | _BV(UCSZ00);
    uart_enabled = 1;
}

static void 
uart_off()
{
    // Turn of interrupts and disable tx/rx
    UCSR0B = 0;
    uart_enabled = 0;

    // Power reduction register
    PRR |= _BV(PRUSART0);
}

int 
uart_putchar(char c, FILE *stream)
{
    if (!uart_enabled)
    {
        return EOF;
    }
    // XXX could perhaps sleep in the loop for power.
    if (c == '\n')
    {
        loop_until_bit_is_set(UCSR0A, UDRE0);
        UDR0 = '\r';
    }
    loop_until_bit_is_set(UCSR0A, UDRE0);
    UDR0 = c;
    if (stream == crc_stdout)
    {
        crc_out = _crc_ccitt_update(crc_out, c);
    }
    if (c == '\r')
    {
        loop_until_bit_is_set(UCSR0A, UDRE0);
        UDR0 = '\n';
        if (stream == crc_stdout)
        {
            crc_out = _crc_ccitt_update(crc_out, '\n');
        }
    }
    return (unsigned char)c;
}

static void
cmd_fetch()
{
    crc_out = 0;
    uint8_t n_sensors;
    eeprom_read(n_sensors, n_sensors);

    uint16_t millivolt_vcc, int_temp;

    adc_internal(&millivolt_vcc, &int_temp);

    fprintf_P(crc_stdout, PSTR("START\n"));
    fprintf_P(crc_stdout, PSTR("now=%lu\n"
                                "time_step=%hu\n"
                                "first_time=%lu\n"
                                "last_time=%lu\n"
                                "voltage=%hu\n"
                                "avrtemp=%hu\n"), 
                                clock_epoch, 
                                (uint16_t)MEASURE_WAKE, 
                                first_measurement_clock, 
                                last_measurement_clock,
                                millivolt_vcc,
                                int_temp
                                );
    fprintf_P(crc_stdout, PSTR("sensors=%u\n"), n_sensors);
    for (uint8_t s = 0; s < n_sensors; s++)
    {
        uint8_t id[ID_LEN];
        fprintf_P(crc_stdout, PSTR("sensor_id%u="), s);
        eeprom_read_to(id, sensor_id[s], ID_LEN);
        printhex(id, ID_LEN, crc_stdout);
        fputc('\n', crc_stdout);
    }
    fprintf_P(crc_stdout, PSTR("measurements=%hu\n"), n_measurements);
    for (uint16_t n = 0; n < n_measurements; n++)
    {
        fprintf_P(crc_stdout, PSTR("meas%hu="), n);
        for (uint8_t s = 0; s < n_sensors; s++)
        {
            fprintf_P(crc_stdout, PSTR(" %hu"), measurements[n][s]);
        }
        fputc('\n', crc_stdout);
    }
    fprintf_P(crc_stdout, PSTR("END\n"));
    fprintf_P(stdout, PSTR("CRC=%hu\n"), crc_out);
}

static void
cmd_clear()
{
    n_measurements = 0;
    printf_P(PSTR("cleared\n"));
}

static void
cmd_btoff()
{
    comms_count = 0;
    printf_P(PSTR("off:%hu\n"), COMMS_WAKE);
    _delay_ms(100);
    comms_timeout = 0;
}

static void
cmd_awake()
{
    comms_timeout = WAKE_SECS;
    printf_P(PSTR("awake %hu\n"), WAKE_SECS);
}

static void
cmd_reset()
{
    printf_P(PSTR("reset\n"));
    _delay_ms(100);
    cli(); // disable interrupts 
    wdt_enable(WDTO_15MS); // enable watchdog 
    while(1); // wait for watchdog to reset processor 
}

static void
cmd_measure()
{
    printf_P(PSTR("measuring\n"));
    need_measurement = 1;
}

static void
cmd_sensors()
{
    uint8_t ret = simple_ds18b20_start_meas(NULL);
    printf_P(PSTR("All sensors, ret %d, waiting...\n"), ret);
    long_delay(DS18B20_TCONV_12BIT);
    simple_ds18b20_read_all();
}

#if 0
// 0 on success
static uint8_t
get_hex_string(const char *hex, uint8_t *out, uint8_t size)
{
    uint8_t upper;
    uint8_t o;
    for (uint8_t i = 0, z = 0; o < size; i++)
    {
        uint8_t h = hex[i];
        if (h >= 'A' && h <= 'F')
        {
            // lower case
            h += 0x20;
        }
        uint8_t nibble;
        if (h >= '0' && h <= '9')
        {
            nibble = h - '0';
        }
        else if (h >= 'a' && h <= 'f')
        {
            nibble = 10 + h - 'a';
        }
        else if (h == ' ' || h == ':')
        {
            continue;
        }
        else
        {
            printf_P(PSTR("Bad hex 0x%x '%c'\n"), hex[i], hex[i]);
            return 1;
        }

        if (z % 2 == 0)
        {
            upper = nibble << 4;
        }
        else
        {
            out[o] = upper | nibble;
            o++;
        }

        z++;
    }

    if (o != size)
    {
        printf_P(PSTR("Short hex\n"));
        return 1;
    }
    return 0;
}
#endif

static void
add_sensor(uint8_t *id)
{
    uint8_t n;
    eeprom_read(n, n_sensors);
    if (n < MAX_SENSORS)
    {
        cli();
        eeprom_write_from(id, sensor_id[n], ID_LEN);
        n++;
        eeprom_write(n, n_sensors);
        sei();
        printf_P(PSTR("Added sensor %d : "), n);
        printhex(id, ID_LEN, stdout);
        putchar('\n');
    }
    else
    {
        printf_P(PSTR("Too many sensors\n"));
    }
}

static void
cmd_add_all()
{
    uint8_t id[OW_ROMCODE_SIZE];
    printf_P("Adding all\n");
    ow_reset();
    for( uint8_t diff = OW_SEARCH_FIRST; diff != OW_LAST_DEVICE; )
    {
        diff = ow_rom_search( diff, &id[0] );
        if( diff == OW_PRESENCE_ERR ) {
            printf_P( PSTR("No Sensor found\r") );
            return;
        }
        
        if( diff == OW_DATA_ERR ) {
            printf_P( PSTR("Bus Error\r") );
            return;
        }
        add_sensor(id);
    }
}

static void
cmd_init()
{
    printf_P(PSTR("Resetting sensor list\n"));
    uint8_t zero = 0;
    cli();
    eeprom_write(zero, n_sensors);
    sei();
    printf_P(PSTR("Done.\n"));
}

static void
check_first_startup()
{
    uint16_t magic;
    eeprom_read(magic, magic);
    if (magic != EXPECT_MAGIC)
    {
        printf_P(PSTR("First boot, looking for sensors...\n"));
        // in case of power fumbles don't want to reset during eeprom write,
        long_delay(2);
        cmd_init();
        cmd_add_all();
        cli();
        magic = EXPECT_MAGIC;
        eeprom_write(magic, magic);
        sei();
    }
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
    else if (strcmp_P(readbuf, PSTR("measure")) == 0)
    {
        cmd_measure();
    }
    else if (strcmp_P(readbuf, PSTR("sensors")) == 0)
    {
        cmd_sensors();
    }
    else if (strcmp_P(readbuf, PSTR("addall"))== 0)
    {
        cmd_add_all();
    }
    else if (strcmp_P(readbuf, PSTR("awake"))== 0)
    {
        cmd_awake();
    }
    else if (strcmp_P(readbuf, PSTR("init")) == 0)
    {
        cmd_init();
    }
    else if (strcmp_P(readbuf, PSTR("reset")) == 0)
    {
        cmd_reset();
    }
    else
    {
        printf_P(PSTR("Bad command\n"));
    }
}

ISR(INT0_vect)
{
    need_comms = 1;
    comms_timeout = WAKE_SECS;
    blink();
    _delay_ms(100);
    blink();
}


ISR(USART_RX_vect)
{
    char c = UDR0;
#ifdef HAVE_UART_ECHO
    uart_putchar(c, NULL);
#endif
    if (c == '\r' || c == '\n')
    {
        if (readpos > 0)
        {
            readbuf[readpos] = '\0';
            have_cmd = 1;
            readpos = 0;
        }
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
    TCNT2 = 0;
    measure_count ++;
    comms_count ++;

    clock_epoch ++;

    if (comms_timeout != 0)
    {
        comms_timeout--;
    }

    if (measure_count >= MEASURE_WAKE)
    {
        measure_count = 0;
        need_measurement = 1;
    }

    if (comms_count >= COMMS_WAKE)
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
adc_internal(uint16_t *millivolt_vcc, uint16_t *int_temp)
{
    PRR &= ~_BV(PRADC);
    
    // ADPS2 = /16 prescaler, 62khz at 1mhz clock
    ADCSRA = _BV(ADEN) | _BV(ADPS2);

    // set to measure 1.1 reference
    ADMUX = _BV(REFS0) | _BV(MUX3) | _BV(MUX2) | _BV(MUX1);
    ADCSRA |= _BV(ADSC);
    loop_until_bit_is_clear(ADCSRA, ADSC);
    uint8_t low_11 = ADCL;
    uint8_t high_11 = ADCH;
    uint16_t f_11 = low_11 + (high_11 << 8);

    float res_volts = 1.1 * 1024 / f_11;
    *millivolt_vcc = 1000 * res_volts;

    // measure AVR internal temperature against 1.1 ref.
    ADMUX = _BV(MUX3) | _BV(REFS1) | _BV(REFS0);
    ADCSRA |= _BV(ADSC);
    loop_until_bit_is_clear(ADCSRA, ADSC);
    uint8_t low_temp = ADCL;
    uint8_t high_temp = ADCH;
    uint16_t res_internal = low_temp + (high_temp << 8);
    float internal_volts = res_internal * (1.1 / 1024.0);
    // millivolts
    *int_temp = internal_volts * 1000;

    PRR |= _BV(PRADC);
    ADCSRA = 0;
}

#if 0
// untested
static void 
do_adc_335()
{
    //PRR &= ~_BV(PRADC);

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
    // XXX fixme
    //measurements[n_measurements] = temp;
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
    // XXX fixme
    //internal_measurements[n_measurements] = internal_temp;

    printf_P("measure %d: external %d, internal %d, 1.1 %d\n",
            n_measurements, temp, internal_temp, f_11);

    n_measurements++;
    //PRR |= _BV(PRADC);
}
#endif

static void
do_measurement()
{
    uint8_t n_sensors;
    eeprom_read(n_sensors, n_sensors);

    simple_ds18b20_start_meas(NULL);
    _delay_ms(DS18B20_TCONV_12BIT);

    if (n_measurements == NUM_MEASUREMENTS)
    {
        n_measurements = 0;
    }

    for (uint8_t s = 0; s < MAX_SENSORS; s++)
    {
        int16_t decicelsius;
        if (s >= n_sensors)
        {
            decicelsius = VALUE_NOSENSOR;
        }
        else
        {
            uint8_t id[ID_LEN];
            eeprom_read_to(id, sensor_id[s], ID_LEN);

            uint8_t ret = simple_ds18b20_read_decicelsius(id, &decicelsius);
            if (ret != DS18X20_OK)
            {
                decicelsius = VALUE_BROKEN;
            }
        }
        measurements[n_measurements][s] = decicelsius;
    }

    if (n_measurements == 0)
    {
        first_measurement_clock = clock_epoch;
    }
    last_measurement_clock = clock_epoch;

    n_measurements++;
    //do_adc_335();
}

static void
do_comms()
{
    // turn on bluetooth
    set_aux_power(1);
    uart_on();
    
    // write sd card here? same 3.3v regulator...
    
    for (comms_timeout = WAKE_SECS; comms_timeout > 0;  )
    {
        if (need_measurement)
        {
            need_measurement = 0;
            do_measurement();
            continue;
        }

        if (have_cmd)
        {
            have_cmd = 0;
            read_handler();
            continue;
        }

        // wait for commands from the master
        idle_sleep();
    }

    uart_off();
    // in case bluetooth takes time to flush
    _delay_ms(100);
    set_aux_power(0);
}

static void
blink()
{
    PORT_LED &= ~_BV(PIN_LED);
    _delay_ms(1);
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

ISR(BADISR_vect)
{
    //uart_on();
    printf_P(PSTR("Bad interrupt\n"));
}

int main(void)
{
    setup_chip();
    blink();

    set_aux_power(0);

    stdout = &mystdout;
    uart_on();

    printf(PSTR("Started.\n"));

    check_first_startup();

    uart_off();

    // turn off everything except timer2
    PRR = _BV(PRTWI) | _BV(PRTIM0) | _BV(PRTIM1) | _BV(PRSPI) | _BV(PRUSART0) | _BV(PRADC);

    // for testing
    uart_on();

    setup_tick_counter();

    sei();

    need_comms = 1;
    need_measurement = 1;

    for(;;)
    {
        if (need_measurement)
        {
            need_measurement = 0;
            do_measurement();
            continue;
        }

        if (need_comms)
        {
            need_comms = 0;
            do_comms();
            continue;
        }

        deep_sleep();
        if (clock_epoch % 60 == 0)
        {
            blink();
        }
    }

    return 0;   /* never reached */
}
