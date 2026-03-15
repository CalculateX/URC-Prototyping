#include <iostream>
#include <cstring>
#include <net/if.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <linux/can.h>
#include <linux/can/raw.h>
#include <unistd.h>

extern "C" {
    int soc;

    // Initializes the CAN socket for the specified interface (e.g., "can1")
    void init_motor(const char* iface, int motor_id) {
        struct sockaddr_can addr;
        struct ifreq ifr;

        soc = socket(PF_CAN, SOCK_RAW, CAN_RAW);
        strcpy(ifr.ifr_name, iface);
        ioctl(soc, SIOCGIFINDEX, &ifr);

        addr.can_family = AF_CAN;
        addr.can_ifindex = ifr.ifr_ifindex;

        bind(soc, (struct sockaddr *)&addr, sizeof(addr));
    }

    // Sends the power command to the SparkMax
    // Uses the FRC CAN protocol bit-packing for the Extended ID
    void set_power(int motor_id, float power) {
        struct can_frame frame;
        
        // FRC Extended ID bitmask for a Duty Cycle command
        // Device Type: 2 (Motor Controller)
        // Manufacturer: 21 (REV Robotics)
        // API Index: 2 (Duty Cycle)
        uint32_t can_id = 0x02050000; 
        can_id |= (motor_id & 0x3F); // Add Device ID
        
        frame.can_id = can_id | CAN_EFF_FLAG; // Mark as Extended Frame
        frame.can_dlc = 8;

        // Convert float power (-1.0 to 1.0) to 32-bit float bytes
        memcpy(frame.data, &power, sizeof(float));
        memset(frame.data + 4, 0, 4);

        send(soc, &frame, sizeof(struct can_frame), 0);
    }
}
