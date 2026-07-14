#ifndef PACKET_H
#define PACKET_H

#include <string>
#include <stdint.h>

class Packet {
public:
    int rssi;
    uint64_t timestamp; // Timestamp in milliseconds since boot
    std::string mac;
    int channel;        // Advertising channel index (e.g. 37, 38, 39, or -1 if unavailable)

    Packet(int r, uint64_t t, const std::string& m, int c = -1) 
        : rssi(r), timestamp(t), mac(m), channel(c) {}
};

#endif // PACKET_H
