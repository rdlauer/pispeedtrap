import time
import serial


def send_serial_cmd(print_prefix, command):
    """
    function for sending serial commands to the OPS module
    """
    data_for_send_str = command
    data_for_send_bytes = str.encode(data_for_send_str)
    print(print_prefix, command)
    ser.write(data_for_send_bytes)
    # initialize message verify checking
    ser_message_start = '{'
    ser_write_verify = False
    # print out module response to command string
    while not ser_write_verify:
        data_rx_bytes = ser.readline()
        data_rx_length = len(data_rx_bytes)
        if data_rx_length != 0:
            data_rx_str = str(data_rx_bytes)
            if data_rx_str.find(ser_message_start):
                ser_write_verify = True


ser = serial.Serial(
    port='/dev/ttyACM0',
    baudrate=9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1,
    writeTimeout=2
)
ser.flushInput()
ser.flushOutput()

# constants for the OPS module
Ops_Speed_Output_Units = ['US', 'UK', 'UM', 'UC']
Ops_Speed_Output_Units_lbl = ['mph', 'km/h', 'm/s', 'cm/s']
Ops_Blanks_Pref_Zero = 'BZ'
Ops_Sampling_Frequency = 'SX'
Ops_Transmit_Power = 'PX'
Ops_Threshold_Control = 'MX'
Ops_Module_Information = '??'
Ops_Overlook_Buffer = 'OZ'

# initialize the OPS module
send_serial_cmd("\nOverlook buffer", Ops_Overlook_Buffer)
send_serial_cmd("\nSet Speed Output Units: ", Ops_Speed_Output_Units[0])
send_serial_cmd("\nSet Sampling Frequency: ", Ops_Sampling_Frequency)
send_serial_cmd("\nSet Transmit Power: ", Ops_Transmit_Power)
send_serial_cmd("\nSet Threshold Control: ", Ops_Threshold_Control)
send_serial_cmd("\nSet Blanks Preference: ", Ops_Blanks_Pref_Zero)
# send_serial_cmd("\nModule Information: ", Ops_Module_Information)


def ops_get_speed():
    """
    capture speed reading from OPS module
    """
    #captured_speeds = []
    while True:
        speed_available = False
        Ops_rx_bytes = ser.readline()
        # check for speed information from OPS module
        Ops_rx_bytes_length = len(Ops_rx_bytes)
        if Ops_rx_bytes_length != 0:
            Ops_rx_str = str(Ops_rx_bytes)
            # print("RX:"+Ops_rx_str)
            if Ops_rx_str.find('{') == -1:
                # speed data found
                try:
                    Ops_rx_float = float(Ops_rx_bytes)
                    speed_available = True
                except ValueError:
                    print("Unable to convert to a number the string: " + Ops_rx_str)
                    speed_available = False

        if speed_available == True:
            speed_rnd = round(Ops_rx_float)

            return float(speed_rnd)
