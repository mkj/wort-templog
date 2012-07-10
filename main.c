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
#include <util/atomic.h>
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

// TICK should be 8 or less (8 untested). all timers need
// to be a multiple.

#define TICK 6
// we have 1024 prescaler, 32768 crystal.
#define SLEEP_COMPARE (32*TICK-1)

#define VALUE_NOSENSOR 0x07D0 // 125 degrees
#define VALUE_BROKEN 0x07D1 // 125.0625

#define BAUD 19200
#define UBRR ((F_CPU)/8/(BAUD)-1)

#define PORT_LED PORTC
#define DDR_LED DDRC
#define PIN_LED PC4

#define PORT_SHDN PORTD
#define DDR_SHDN DDRD
#define PIN_SHDN PD7

// total amount of 16bit values available for measurements.
// adjust emperically, be sure to allow enough stack space too
#define TOTAL_MEASUREMENTS 840

// each sensor slot uses 8 bytes
#define MAX_SENSORS 6

// fixed at 8, have a shorter name
#define ID_LEN OW_ROMCODE_SIZE

// #define HAVE_UART_ECHO

// eeprom-settable parameters. all timeouts should
// be a multiple of TICK (6 seconds probably)
static uint16_t measure_wake = 120;
static uint16_t comms_wake = 3600;
static uint8_t wake_secs = 30;

// ---- Atomic guards required accessing these variables
static uint32_t clock_epoch;
static uint16_t comms_count;
static uint16_t measure_count;
// ---- End atomic guards required

static uint16_t n_measurements;

// calculated at startup as TOTAL_MEASUREMENTS/n_sensors
static uint16_t max_measurements;

static uint16_t measurements[TOTAL_MEASUREMENTS];
static uint32_t first_measurement_clock;
// last_measurement_clock is redundant but checks that we're not missing
// samples
static uint32_t last_measurement_clock;

static uint32_t last_comms_clock;

// boolean flags
static uint8_t need_measurement;
static uint8_t need_comms;
static uint8_t uart_enabled;
static uint8_t stay_awake;

// counts down from WAKE_SECS to 0, goes to deep sleep when hits 0
static uint8_t comms_timeout;

static uint8_t readpos;
static char readbuf[30];
static uint8_t have_cmd;

static uint8_t n_sensors;
static uint8_t sensor_id[MAX_SENSORS][ID_LEN];


int uart_putchar(char c, FILE *stream);
static void long_delay(int ms);
static void blink();
static uint16_t adc_vcc();

static FILE mystdout = FDEV_SETUP_STREAM(uart_putchar, NULL,
        _FDEV_SETUP_WRITE);

static uint16_t crc_out;
static FILE _crc_stdout = FDEV_SETUP_STREAM(uart_putchar, NULL,
        _FDEV_SETUP_WRITE);
// convenience
static FILE *crc_stdout = &_crc_stdout;


// thanks to http://projectgus.com/2010/07/eeprom-access-with-arduino/
#define eeprom_read_to(dst_p, eeprom_field, dst_size) eeprom_read_block((dst_p), (void *)offsetof(struct __eeprom_data, eeprom_field), (dst_size))
#define eeprom_read(dst, eeprom_field) eeprom_read_to((&dst), eeprom_field, sizeof(dst))
#define eeprom_write_from(src_p, eeprom_field, src_size) eeprom_write_block((src_p), (void *)offsetof(struct __eeprom_data, eeprom_field), (src_size))
#define eeprom_write(src, eeprom_field) { eeprom_write_from(&src, eeprom_field, sizeof(src)); }

#define EXPECT_MAGIC 0x67c9

struct __attribute__ ((__packed__)) __eeprom_data {
    // XXX eeprom unused at present
    uint16_t magic;
    uint16_t measure_wake;
    uint16_t comms_wake;
    uint8_t wake_secs;
};

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
set_measurement(uint8_t sensor, uint16_t measurement, uint16_t reading)
{
    measurements[sensor*max_measurements + measurement] = reading;
}

static uint16_t 
get_measurement(uint8_t sensor, uint16_t measurement)
{
    return measurements[sensor*max_measurements + measurement];
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

    fprintf_P(crc_stdout, PSTR("START\n"));
    {
        uint32_t epoch_copy;
        ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
        {
            epoch_copy = clock_epoch;
        }
        fprintf_P(crc_stdout, PSTR("now=%lu\n"), epoch_copy);
    }
    fprintf_P(crc_stdout, PSTR("time_step=%hu\n"), measure_wake);
    fprintf_P(crc_stdout, PSTR("first_time=%lu\n"), first_measurement_clock);
    fprintf_P(crc_stdout, PSTR("last_time=%lu\n"),  last_measurement_clock);
    fprintf_P(crc_stdout, PSTR("comms_time=%lu\n"), last_comms_clock);
    fprintf_P(crc_stdout, PSTR("voltage=%hu\n"), adc_vcc());
    fprintf_P(crc_stdout, PSTR("sensors=%hhu\n"), n_sensors);
    for (uint8_t s = 0; s < n_sensors; s++)
    {
        fprintf_P(crc_stdout, PSTR("sensor_id%hhu="), s);
        printhex(sensor_id[s], ID_LEN, crc_stdout);
        fputc('\n', crc_stdout);
    }
    fprintf_P(crc_stdout, PSTR("measurements=%hu\n"), n_measurements);
    for (uint16_t n = 0; n < n_measurements; n++)
    {
        fprintf_P(crc_stdout, PSTR("meas%hu="), n);
        for (uint8_t s = 0; s < n_sensors; s++)
        {
            fprintf_P(crc_stdout, PSTR(" %04hx"), get_measurement(s, n));
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
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
    {
        comms_count = 0;
    }
    printf_P(PSTR("off:%hu\n"), comms_wake);
    _delay_ms(100);
    comms_timeout = 0;
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
    printf_P(PSTR("All sensors, ret %hhu, waiting...\n"), ret);
    long_delay(DS18B20_TCONV_12BIT);
    simple_ds18b20_read_all();
}

static void
init_sensors()
{
    uint8_t id[OW_ROMCODE_SIZE];
    printf_P(PSTR("init sensors\n"));
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

        if (n_sensors < MAX_SENSORS)
        {
            memcpy(sensor_id[n_sensors], id, ID_LEN);
            printf_P(PSTR("Added sensor %hhu : "), n_sensors);
            printhex(id, ID_LEN, stdout);
            putchar('\n');
            n_sensors++;
        }
        else
        {
            printf_P(PSTR("Too many sensors\n"));
        }
    }

    max_measurements = TOTAL_MEASUREMENTS / n_sensors;
}

static void
load_params()
{
    uint16_t magic;
    eeprom_read(magic, magic);
    if (magic == EXPECT_MAGIC)
    {
        eeprom_read(measure_wake, measure_wake);
        eeprom_read(comms_wake, comms_wake);
        eeprom_read(wake_secs, wake_secs);
    }
}

static void
cmd_get_params()
{
    printf_P(PSTR("measure %hu\n"), measure_wake);
    printf_P(PSTR("comms %hu\n"), comms_wake);
    printf_P(PSTR("wake %hhu\n"), wake_secs);
    printf_P(PSTR("tick %d\n"), TICK);
    printf_P(PSTR("sensors %hhu (%hhu)\n"), 
            n_sensors, MAX_SENSORS);
    printf_P(PSTR("meas %hu (%hu)\n"),
            max_measurements, TOTAL_MEASUREMENTS);
}

static void
cmd_set_params(const char *params)
{
    uint16_t new_measure_wake;
    uint16_t new_comms_wake;
    uint8_t new_wake_secs;
    int ret = sscanf_P(params, PSTR("%hu %hu %hhu"),
            &new_measure_wake, &new_comms_wake, &new_wake_secs);

    if (ret != 3)
    {
        printf_P(PSTR("Bad values\n"));
    }
    else
    {
        cli();
        eeprom_write(new_measure_wake, measure_wake);
        eeprom_write(new_comms_wake, comms_wake);
        eeprom_write(new_wake_secs, wake_secs);
        uint16_t magic = EXPECT_MAGIC;
        eeprom_write(magic, magic);
        sei();
        printf_P(PSTR("set_params for next boot\n"));
        printf_P(PSTR("measure %hu comms %hu wake %hhu\n"),
                new_measure_wake, new_comms_wake, new_wake_secs);
    }
}

static void
cmd_awake()
{
    stay_awake = 1;
    printf_P(PSTR("awake\n"));
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
    else if (strcmp_P(readbuf, PSTR("get_params")) == 0)
    {
        cmd_get_params();
    }
    else if (strncmp_P(readbuf, PSTR("set_params "), 
                strlen("set_params ") == 0))
    {
        cmd_set_params(&readbuf[strlen("set_params ")]);
    }
    else if (strcmp_P(readbuf, PSTR("awake")) == 0)
    {
        cmd_awake();
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
    comms_timeout = wake_secs;
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
    measure_count += TICK;
    comms_count += TICK;

    clock_epoch += TICK;

    if (comms_timeout != 0)
    {
        comms_timeout -= TICK;
    }

    if (measure_count >= measure_wake)
    {
        measure_count = 0;
        need_measurement = 1;
    }

    if (comms_count >= comms_wake)
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

static uint16_t
adc_vcc()
{
    PRR &= ~_BV(PRADC);
    
    // /16 prescaler
    ADCSRA = _BV(ADEN) | _BV(ADPS2);

    // set to measure 1.1 reference
    ADMUX = _BV(REFS0) | _BV(MUX3) | _BV(MUX2) | _BV(MUX1);
    // average a number of samples
    uint16_t sum = 0;
    uint8_t num = 0;
    for (uint8_t n = 0; n < 20; n++)
    {
        ADCSRA |= _BV(ADSC);
        loop_until_bit_is_clear(ADCSRA, ADSC);

        uint8_t low_11 = ADCL;
        uint8_t high_11 = ADCH;
        uint16_t val = low_11 + (high_11 << 8);

        if (n >= 4)
        {
            sum += val;
            num++;
        }
    }
    ADCSRA = 0;
    PRR |= _BV(PRADC);

    //float res_volts = 1.1 * 1024 * num / sum;
    //return 1000 * res_volts;
    return ((uint32_t)1100*1024*num) / sum;
}

static void
do_measurement()
{
    blink();

    simple_ds18b20_start_meas(NULL);
    // sleep rather than using a long delay
    deep_sleep();
    //_delay_ms(DS18B20_TCONV_12BIT);

    if (n_measurements == max_measurements)
    {
        n_measurements = 0;
    }

    for (uint8_t s = 0; s < n_sensors; s++)
    {
        uint16_t reading;
        uint8_t ret = simple_ds18b20_read_raw(sensor_id[s], &reading);
        if (ret != DS18X20_OK)
        {
            reading = VALUE_BROKEN;
        }
        set_measurement(s, n_measurements, reading);
    }

    ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
    {
        if (n_measurements == 0)
        {
            first_measurement_clock = clock_epoch;
        }
        last_measurement_clock = clock_epoch;
    }

    n_measurements++;
    //do_adc_335();
}

static void
do_comms()
{
    // turn on bluetooth
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
    {
        last_comms_clock = clock_epoch;
    }
    set_aux_power(1);
    uart_on();
    
    // write sd card here? same 3.3v regulator...
    
    for (comms_timeout = wake_secs; 
        comms_timeout > 0 || stay_awake;  
        )
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

    load_params();

    init_sensors();

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
    }

    return 0;   /* never reached */
}
