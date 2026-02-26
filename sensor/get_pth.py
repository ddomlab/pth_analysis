import time
import serial  # https://pypi.org/project/pyserial/
import crccheck 
port = '/dev/ttyACM0'
interval = 1000

crc_checker = crccheck.crc.CrcXmodem()

def get_pth():
    finaloutput: dict[str, list[str | float]] = {}
    with serial.Serial(port) as ser:
        ser.readlines(2)  # Discard the first two lines as they may be partial

        ser.write(b"INFO\n")  # Get the info line

        time.sleep(0.3)  # Allow 100 ms for request to complete
        ser.write(b"POLL %d\n" % interval)  # Set poll interval

        time.sleep(0.3)
        ser.write(b"FRAC 2\n")  # Return data with two digits past the decimal

        info_line: list = []
        padlen = 0

        # Process all lines in a loop
        for i in range(8):
            line = ser.readline()
            t_str: str = time.ctime()
            t_int: int = int(time.time())
            bytedata: bytes = b""
            if not line:
                break

            # Check data integrity using CRC-16-CCITT (XMODEM)
            try:
                bytedata, crc = line.split(b"*")
                crc = int(crc, 16)  # parse hexadecimal string into an integer variable
                crc_checker.process(bytedata)
                computed_crc = crc_checker.final()
                crc_checker.reset()
                crc_success = computed_crc == crc
            except ValueError:
                # We will get here if there isn't exactly one '*' character in the line.
                # If that's the case, data is most certainly corrupt!
                crc_success = False

            if not crc_success:
                print("Data integrity error")
                break

            # Decode bytes into a list of strings
            data: list = bytedata.decode("ASCII").replace('ERROR', '-1').strip(",").split(",")

            if data[0] == "I":
                if data[1] == "Product ID":  # For the INFO command response
                    info_line = data
                    padlen = max(len(s) for s in info_line[4::2])
                    # print(", ".join(info_line))
                else:  # Other info lines only need the message to be echoed
                    # print(data[3])
                    pass
            else:
                # Create an ID for the device
                device = f"{data[1]} {data[2]}"

                # Convert number strings to the appropriate numerical format
                for i in range(4, len(data), 2):
                    try:
                        data[i] = int(data[i])
                    except ValueError:
                        data[i] = float(data[i])

                # Convert data to a tuple of (sensor, value, unit) triads
                output = zip(info_line[4::2], data[4::2], data[5::2])

                # Display the current time, product id and serial number before every point
                # print(f"\n{t}, {device}")
                finaloutput["time"] = [t_int]
                for d in output:
                    # print(("{:" + str(padlen + 2) + "}{} {}").format(*d))
                    try:
                        finaloutput[d[0]].append(d[1])
                    except KeyError:
                        finaloutput[d[0]] = [d[1]]
        return finaloutput
def get_avg_pth():
    data = get_pth()
    avgdata: dict[str, float | str] = {}
    for key in data:
        if key == "time":
            avgdata[key] = data[key][0]
        else:
            avgdata[key] = round(sum(float(x) for x in data[key]) / len(data[key]), 2)
    return avgdata

if __name__ == "__main__":
    get_pth()