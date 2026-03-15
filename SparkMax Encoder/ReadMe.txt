### SPARK MAX Encoder and Telemetry Diagnostic

**Overview**
The 'get_encoder_values.py' script targets a single SPARK MAX motor controller to verify control and feedback loops. It uses a hybrid approach: sending power commands via a C++ bridge while simultaneously decoding real-time telemetry directly from the CAN bus using Python's SocketCAN interface.

**Configuration Variables**
* MOTOR_ID: The CAN ID of the target SPARK MAX (Default is 3).
* TEST_POWER: The open-loop duty cycle percentage (e.g., 0.50 for 50% power).
* GEAR_RATIO: The reduction ratio used to convert raw motor rotations into physical joint rotations (e.g., 45.0 for a 45:1 gearbox).

**Key Features**
* Firmware v24+ Compatibility: Specifically decodes the 0x2E0 (Status 0) and 0x2E2 (Status 2) frames used in recent firmware versions.
* High-Resolution Feedback: Decodes 32-bit IEEE floating-point values for Motor Velocity (RPM) and Position (Rotations).
* Electrical Diagnostics: Parses 12-bit fixed-point data to provide live readings for Bus Voltage and Phase Current. 
* Hardware Abstraction: Automatically maps internal motor data to actual joint states based on the provided gear ratio.

**Requirements**
* The 'can1' interface must be up and configured for a 1Mbps bitrate.
* Periodic Status Frames 0 and 2 must be enabled/configured on the SPARK MAX via the REV Hardware Client.
