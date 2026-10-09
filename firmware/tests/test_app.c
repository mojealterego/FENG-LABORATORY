#include "thermo_iot_app.h"
#include <stdio.h>
#include <string.h>
#define ASSERT(test) do {if(!(test)){fprintf(stderr,"line %d: %s\n",__LINE__,#test);return 1;}}while(0)

typedef struct {
  uint16_t voltage;
  uint32_t net_uw;
  int32_t temp;
  int32_t teg_uw;
  bool joined;
  bool radio_accepts;
  bool read_success;
  int join_calls;
  int tx_calls;
  uint8_t last_port;
  uint8_t last_data[8];
} bench;

static bool voltage(void *v, uint16_t *out) {
  bench *b=(bench *)v;
  if(!b->read_success)return false;
  *out=b->voltage;
  return true;
}
static bool net(void *v, uint32_t *out) {
  bench *b=(bench *)v;
  if(!b->read_success)return false;
  *out=b->net_uw;
  return true;
}
static bool temp(void *v, int32_t *out) {
  bench *b=(bench *)v;
  if(!b->read_success)return false;
  *out=b->temp;
  return true;
}
static bool teg(void *v, int32_t *out) {
  bench *b=(bench *)v;
  if(!b->read_success)return false;
  *out=b->teg_uw;
  return true;
}
static bool joined(void *v) {
  return ((bench *)v)->joined;
}
static bool join(void *v) {
  bench *b=(bench *)v;b->join_calls++;
  return b->radio_accepts;
}
static bool tx(void *v, uint8_t port, const uint8_t *p, uint8_t len) {
  bench *b=(bench *)v;b->tx_calls++;b->last_port=port;
  if(len!=8u)return false;
  memcpy(b->last_data,p,8);
  return b->radio_accepts;
}
static thermo_iot_platform connect(bench *b) {
  thermo_iot_platform result={
    b,voltage,net,temp,teg,joined,join,tx
  };
  return result;
}
static thermo_iot_power_config config(void) {
  thermo_iot_power_config c={
    .voltage_start_mv=2700,.voltage_stop_mv=2400,
    .min_interval_s=60,.max_interval_s=3600,.duty_interval_s=60,
    .cycle_energy_uj=21900,.energy_margin_percent=200
  };
  return c;
}
int main(void) {
  bench b={.voltage=3000,.net_uw=1000,.temp=4300,.teg_uw=150,
           .joined=false,.radio_accepts=true,.read_success=true};
  thermo_iot_app app;
  thermo_iot_platform platform=connect(&b);
  thermo_iot_power_config c=config();
  ASSERT(!thermo_iot_app_init(NULL,&platform,&c));
  ASSERT(thermo_iot_app_init(&app,&platform,&c));
  ASSERT(thermo_iot_app_step(&app,0)==THERMO_IOT_APP_JOIN_REQUESTED);
  ASSERT(b.join_calls==1 && b.tx_calls==0);
  ASSERT(thermo_iot_app_step(&app,10)==THERMO_IOT_APP_WAIT);
  ASSERT(b.join_calls==1);
  b.joined=true;
  ASSERT(thermo_iot_app_step(&app,60)==THERMO_IOT_APP_UPLINK_QUEUED);
  ASSERT(b.tx_calls==1 && b.last_port==10);
  ASSERT(b.last_data[0]==1 && b.last_data[1]==0xCC && b.last_data[2]==0x10);
  ASSERT(thermo_iot_app_step(&app,61)==THERMO_IOT_APP_WAIT);
  b.voltage=2390;
  ASSERT(thermo_iot_app_step(&app,120)==THERMO_IOT_APP_CHARGING);
  b.voltage=2700;
  b.net_uw=0;
  ASSERT(thermo_iot_app_step(&app,180)==THERMO_IOT_APP_DEFICIT);
  b.net_uw=1000;
  b.radio_accepts=false;
  ASSERT(thermo_iot_app_step(&app,240)==THERMO_IOT_APP_RADIO_REJECTED);
  ASSERT(b.tx_calls==2);
  b.read_success=false;
  ASSERT(thermo_iot_app_step(&app,300)==THERMO_IOT_APP_READ_ERROR);
  b.read_success=true;
  b.voltage=3000;
  b.radio_accepts=true;
  b.temp=15500;
  ASSERT(thermo_iot_app_step(&app,360)==THERMO_IOT_APP_INVALID);
  ASSERT(b.tx_calls==2);
  ASSERT(thermo_iot_app_step(&app,359)==THERMO_IOT_APP_INVALID);
  puts("Thermo-IoT STM32WLE5JC application logic host tests: PASS");
  return 0;
}
