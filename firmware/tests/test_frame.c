/* C11 host-side golden-vector and range tests for the reference binary payload. */

#include "thermo_iot_frame.h"
#include <stdio.h>
#include <string.h>

#define CHECK(expr) do { if (!(expr)) { fprintf(stderr, "CHECK failed: %s:%d: %s\n", __FILE__, __LINE__, #expr); return 1; } } while (0)

int main(void) {
    uint8_t wire[THERMO_IOT_FRAME_LEN] = {0};
    const uint8_t expected[THERMO_IOT_FRAME_LEN] = {1, 0xFE, 0x10, 0x8C, 0x0A, 0x64, 0, 2};
    struct thermo_iot_sample restored = {0};

    CHECK(thermo_iot_encode_frame(4350, 2700, 100, 2, wire));
    CHECK(memcmp(wire, expected, sizeof(expected)) == 0);
    CHECK(thermo_iot_decode_frame(wire, sizeof(wire), &restored));
    CHECK(restored.temperature_centi_c == 4350);
    CHECK(restored.capacitor_mv == 2700);
    CHECK(restored.teg_power_uw == 100);
    CHECK(restored.flags == 2);

    CHECK(thermo_iot_encode_frame(-1250, 3000, -1, 0, wire));
    CHECK(thermo_iot_decode_frame(wire, sizeof(wire), &restored));
    CHECK(restored.temperature_centi_c == -1250);
    CHECK(restored.teg_power_uw == -1);

    CHECK(!thermo_iot_encode_frame(15001, 2700, 100, 0, wire));
    CHECK(!thermo_iot_encode_frame(4300, 5501, 100, 0, wire));
    CHECK(!thermo_iot_encode_frame(4300, 2700, 65535, 0, wire));
    CHECK(!thermo_iot_encode_frame(4300, 2700, 100, 0, NULL));
    CHECK(!thermo_iot_decode_frame(wire, 7, &restored));
    CHECK(!thermo_iot_decode_frame(NULL, 8, &restored));
    CHECK(!thermo_iot_decode_frame(wire, 8, NULL));
    wire[0] = 2;
    CHECK(!thermo_iot_decode_frame(wire, 8, &restored));
    puts("Thermo-IoT C codec: PASS");
    return 0;
}
