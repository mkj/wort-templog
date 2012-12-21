//
//  How to access GPIO registers from C-code on the Raspberry-Pi
//  Example program
//  15-January-2012
//  Dom and Gert
//


// Access from ARM Running Linux

#define BCM2708_PERI_BASE        0x20000000
#define GPIO_BASE                (BCM2708_PERI_BASE + 0x200000) /* GPIO controller */


#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <dirent.h>
#include <fcntl.h>
#include <assert.h>
#include <sys/mman.h>
#include <sys/types.h>
#include <sys/stat.h>

#include <unistd.h>

#define PAGE_SIZE (4*1024)
#define BLOCK_SIZE (4*1024)

int  mem_fd;
char *gpio_mem, *gpio_map;
char *spi0_mem, *spi0_map;


// I/O access
volatile unsigned *gpio;


// GPIO setup macros. Always use INP_GPIO(x) before using OUT_GPIO(x) or SET_GPIO_ALT(x,y)
#define INP_GPIO(g) *(gpio+((g)/10)) &= ~(7<<(((g)%10)*3))
#define OUT_GPIO(g) *(gpio+((g)/10)) |=  (1<<(((g)%10)*3))
#define SET_GPIO_ALT(g,a) *(gpio+(((g)/10))) |= (((a)<=3?(a)+4:(a)==4?3:2)<<(((g)%10)*3))

#define FSEL_OFFSET         0   // 0x0000
#define SET_OFFSET          7   // 0x001c / 4
#define CLR_OFFSET          10  // 0x0028 / 4
#define PINLEVEL_OFFSET     13  // 0x0034 / 4
#define EVENT_DETECT_OFFSET 16  // 0x0040 / 4
#define RISING_ED_OFFSET    19  // 0x004c / 4
#define FALLING_ED_OFFSET   22  // 0x0058 / 4
#define HIGH_DETECT_OFFSET  25  // 0x0064 / 4
#define LOW_DETECT_OFFSET   28  // 0x0070 / 4
#define PULLUPDN_OFFSET     37  // 0x0094 / 4
#define PULLUPDNCLK_OFFSET  38  // 0x0098 / 4


#define GPIO_GET(g) ((*(gpio+PINLEVEL_OFFSET)   & (1<<(g))) >> (g))
#define GPIO_SET(g) (*(gpio+SET_OFFSET) = 1<<(g))  // sets   bits which are 1 ignores bits which are 0
#define GPIO_CLR(g) (*(gpio+CLR_OFFSET) = 1<<(g))// clears bits which are 1 ignores bits which are 0

#define TOUCH_IN 24
#define TOUCH_OUT 25

void setup_io();

int main(int argc, char **argv)
{ 
  int g,rep;

  // Set up gpi pointer for direct register access
  setup_io();

  // Switch GPIO 7..11 to output mode

 /************************************************************************\
  * You are about to change the GPIO settings of your computer.          *
  * Mess this up and it will stop working!                               *
  * It might be a good idea to 'sync' before running this program        *
  * so at least you still have your code changes written to the SD-card! *
 \************************************************************************/


    INP_GPIO(TOUCH_IN);
    INP_GPIO(TOUCH_OUT);
    OUT_GPIO(TOUCH_OUT);

    int num = 1000;
    int sum = 0;

    while (1)
    {
int n;
sum = 0;
    for (n = 0; n < num; n++)
{
            GPIO_CLR(TOUCH_OUT);
            usleep(1000);
            GPIO_SET(TOUCH_OUT);
            while (GPIO_GET(TOUCH_IN) == 0)
            {
                sum++;
            }
        }
    printf("total %f\n", (float)sum / num);
}
    return 0;

} // main


//
// Set up a memory regions to access GPIO
//
void setup_io()
{
   /* open /dev/mem */
   if ((mem_fd = open("/dev/mem", O_RDWR|O_SYNC) ) < 0) {
      printf("can't open /dev/mem \n");
      exit (-1);
   }

   /* mmap GPIO */

   // Allocate MAP block
   if ((gpio_mem = malloc(BLOCK_SIZE + (PAGE_SIZE-1))) == NULL) {
      printf("allocation error \n");
      exit (-1);
   }

   // Make sure pointer is on 4K boundary
   if ((unsigned long)gpio_mem % PAGE_SIZE)
     gpio_mem += PAGE_SIZE - ((unsigned long)gpio_mem % PAGE_SIZE);

   // Now map it
   gpio_map = (unsigned char *)mmap(
      (caddr_t)gpio_mem,
      BLOCK_SIZE,
      PROT_READ|PROT_WRITE,
      MAP_SHARED|MAP_FIXED,
      mem_fd,
      GPIO_BASE
   );

   if ((long)gpio_map < 0) {
      printf("mmap error %d\n", (int)gpio_map);
      exit (-1);
   }

   // Always use volatile pointer!
   gpio = (volatile unsigned *)gpio_map;


} // setup_io
