/* Thermo-IoT laboratory frame codec, C11 reference only. */
#ifndef THERMO_IOT_FRAME_H
#define THERMO_IOT_FRAME_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define THERMO_IOT_FRAME_LEN 8u
#define THERMO_IOT_FRAME_VERSION 1u
#define THERMO_IOT_FPORT 10u

/* teg_power_uw == -1 represents measurement not available. */
struct thermo_iot_sample {
    int32_t temperature_centi_c;
    uint32_t capacitor_mv;
    int32_t teg_power_uw;
    uint8_t flags;
};

/* Writes exactly eight little-endian bytes on success. */
bool thermo_iot_encode_frame(
    int32_t temperature_centi_c,
    uint32_t capacitor_mv,
    int32_t teg_power_uw,
    uint8_t flags,
    uint8_t *output
);

/* Validates version, length and physical bounds before publishing the sample. */
bool thermo_iot_decode_frame(
    const uint8_t *input,
    size_t length,
    struct thermo_iot_sample *sample
);

#endif
