/* Portable binary codec. The LoRaWAN stack and sensor hardware are external. */

#include "thermo_iot_frame.h"

static bool valid_sample(
    int32_t temperature_centi_c, uint32_t capacitor_mv, int32_t teg_power_uw
) {
    return temperature_centi_c >= -4000 && temperature_centi_c <= 15000
        && capacitor_mv <= 5500u
        && teg_power_uw >= -1 && teg_power_uw <= 65534;
}

bool thermo_iot_encode_frame(
    int32_t temperature_centi_c,
    uint32_t capacitor_mv,
    int32_t teg_power_uw,
    uint8_t flags,
    uint8_t *output
) {
    if (output == NULL || !valid_sample(temperature_centi_c, capacitor_mv, teg_power_uw)) {
        return false;
    }
    uint16_t t = (uint16_t)temperature_centi_c;
    uint16_t cap = (uint16_t)capacitor_mv;
    uint16_t teg = teg_power_uw == -1 ? UINT16_MAX : (uint16_t)teg_power_uw;
    output[0] = THERMO_IOT_FRAME_VERSION;
    output[1] = (uint8_t)(t & 0xFFu);
    output[2] = (uint8_t)(t >> 8);
    output[3] = (uint8_t)(cap & 0xFFu);
    output[4] = (uint8_t)(cap >> 8);
    output[5] = (uint8_t)(teg & 0xFFu);
    output[6] = (uint8_t)(teg >> 8);
    output[7] = flags;
    return true;
}

bool thermo_iot_decode_frame(
    const uint8_t *input, size_t length, struct thermo_iot_sample *sample
) {
    if (input == NULL || sample == NULL || length != THERMO_IOT_FRAME_LEN
        || input[0] != THERMO_IOT_FRAME_VERSION) {
        return false;
    }
    uint16_t t = (uint16_t)((uint16_t)input[1] | ((uint16_t)input[2] << 8));
    uint16_t cap = (uint16_t)((uint16_t)input[3] | ((uint16_t)input[4] << 8));
    uint16_t teg = (uint16_t)((uint16_t)input[5] | ((uint16_t)input[6] << 8));
    int32_t temperature = t < 32768u ? (int32_t)t : (int32_t)t - 65536;
    int32_t power = teg == UINT16_MAX ? -1 : (int32_t)teg;
    if (!valid_sample(temperature, cap, power)) {
        return false;
    }
    struct thermo_iot_sample decoded = {
        temperature, (uint32_t)cap, power, input[7]
    };
    *sample = decoded;
    return true;
}
