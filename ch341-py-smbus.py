"""
Original by Karl Palsson, October 2014 <karlp@tweak.net.au>
Modified by Ray Nieport, December 2022

Considered to be released under your choice of MIT/Apache2/BSD-2-Clause License.

Provides generic hooks for reading/writing I2C via CH341 USB Bridge Controller
in I2C/MEM/EPP mode. Tested on CH341A and CH341T_V3, using I2C Master Mode.

TODO: Make this behave more like python smbus2 (be as API compat as possible).
"""


import struct
import usb.core
import usb.util


"""
@brief USB Control Commands
"""
class CtrlCmd():
    READ = 0xc0
    WRITE = 0x40


"""
@brief CH341 USB Commands

Used for general functionality of the CH341. Not fully tested.
"""
class VendorCmd():
    READ_REG = 0x95
    WRITE_REG = 0x9a
    SERIAL = 0xa1
    PRINT = 0xa3
    MODEM = 0xa4
    MEMW = 0xa6 # aka mCH341_PARA_CMD_W0
    MEMR = 0xac # aka mCH341_PARA_CMD_R0
    SPI = 0xa8
    SIO = 0xa9
    I2C = 0xaa
    UIO = 0xab
    I2C_STATUS = 0x52
    I2C_COMMAND = 0x53
    VERSION = 0x5f # at least in serial mode?


"""
@brief CH341 I2C Commands

Used for I2C fucntionality of the CH341.
Not fully tested, but the important ones seem to work.

After STA, you can insert MS|millis, and US|usecs to insert one or more delays.
MS|0 = 250ms wait,
US|0 = ~260usecs?
US|10 is ~10usecs,
US|20 = MS|4 (strange)
US|40 = ? (switched back to 20khz mode)
"""
class I2CCmd():
    STA = 0x74
    STO = 0x75
    OUT = 0x80
    IN = 0xc0
    MAX = 32 # Vendor code (seems like the wrong place for this): min(0x3f, 32)
    SET = 0x60 # Bit 7 apparently SPI bit order, Bit 2 SPI single vs SPI double
    US = 0x40 # Vendor code uses a few of these in 20khz mode...
    MS = 0x50
    DLY = 0x0f
    END = 0x00 # Finish commands with this. Is this really necessary?


"""
@brief CH341 Class for detection, reading, writing, etc.

Attempts to behave like python smbus for compatiblilty.
"""
class CH341():
    # USB Endpoints for interacting with CH341
    EP_OUT = 0x02
    EP_IN = 0x82

    """
    @brief Construct a new CH341 object.
    
    By default, use the VID and PID assigned by the vendor for I2C mode.
    """
    def __init__(self, vid=0x1a86, pid=0x5512):
        dev = usb.core.find(idVendor=vid, idProduct=pid)

        if dev is None:
            raise ConnectionError("Device not found (%x:%x)" % (vid, pid))

        print(f'Found CH341 device ({vid:x}:{pid:x})')

        # These devices only have one that I know of...
        if (dev.bNumConfigurations != 1):
            raise ConnectionError("Device configuration error")
        dev.set_configuration()
        self.dev = dev
        # print("Device USB Protocol: %d", dev.bDeviceProtocol)


    """
    @brief Set the desired I2C speed 

    @param speed [in] clock frequency in KHz - will round down to 20, 100, 400, 750

    @return: None
    """
    def set_speed(self, speed=100):
        if speed < 100:
            sbit = 0
        elif speed < 400:
            sbit = 1
        elif speed < 750:
            sbit = 2
        else:
            sbit = 3

        cmd = [VendorCmd.I2C, I2CCmd.SET | sbit, I2CCmd.END]
        cnt = self.dev.write(self.EP_OUT, cmd)
        if (cnt != len(cmd)):
            raise ConnectionError("Failed to issue I2C Set Speed Command")


    """
    @brief Set I2C START Condition

    @return None
    """
    def __start(self):
        cmd = [VendorCmd.I2C, I2CCmd.STA, I2CCmd.END]
        cnt = self.dev.write(self.EP_OUT, cmd)
        if (cnt != len(cmd)):
            raise ConnectionError("Failed to issue I2C START Command")


    """
    @brief Set I2C STOP Condition

    @return None
    """
    def __stop(self):
        cmd = [VendorCmd.I2C, I2CCmd.STO, I2CCmd.END]
        cnt = self.dev.write(self.EP_OUT, cmd)
        if (cnt != len(cmd)):
            raise ConnectionError("Failed to issue I2C STOP Command")


    """
    @brief Check if a byte sent on the I2C bus has been acknowledged
    
    @return bool: True for ACK, False for NAK
    """
    def __check_ack(self):
        rval = self.dev.read(self.EP_IN, I2CCmd.MAX)
        if ((len(rval) != 1 ) or (rval[0] & 0x80)):
            return False
        else:
            return True


    """
    @brief Write one or more bytes to I2C bus
    
    @param data [in] bytes to write (<=32)

    @return None
    """
    def __write_bytes(self, data):
        cmd = [VendorCmd.I2C, I2CCmd.OUT]
        if type(data) is list:
            print(data)
            for point in data:
                cmd.append(point)
        else:
            cmd.append(data)
        cmd.append(I2CCmd.END)
        cnt = self.dev.write(self.EP_OUT, cmd)
        if (cnt != len(cmd)):
            raise ConnectionError("Failed to issue I2C Send Command")
        if not (self.__check_ack()):
            raise ConnectionError("I2C ACK not received")


    """
    @brief Read one or more bytes from I2C bus

    @param length [in] number of bytes to read (<=32)

    @return array: data read from bus
    """
    def __read_bytes(self, length=1):
        cmd = [VendorCmd.I2C, I2CCmd.IN | length, I2CCmd.END]
        cnt = self.dev.write(self.EP_OUT, cmd)
        if (cnt != len(cmd)):
            raise ConnectionError("Failed to issue I2C Receive Command")

        rval = self.dev.read(self.EP_IN, length, 100) # (const, len, timeout ms)
        if len(rval) != length:
            raise ConnectionError("I2C Received an incorrect number of bytes")
        return rval


    """
    @brief Check if an address is connected to the I2C bus.
            Confirm ACK bit is set by slave.

    @param addr [in] I2C Slave address to check for
    
    @return bool: True if connected, False if not
    """
    def detect(self, addr):
        rVal = True
        try:
            self.__start()
            self.__write_bytes(addr << 1)
            self.__stop()
        except ConnectionError as err:
            print(err)
            rVal = False
        return rVal


    """
    @brief Write one byte to an I2C device

    @param addr [in] I2C address to write to
    @param off [in] register to start wrtiting to
    @param byte [in] data to write

    @return None
    """
    def write_byte_data(self, addr, off, byte):
        try:
            self.__start()
            self.__write_bytes(addr << 1)
            if off is not None:
                self.__write_bytes(off)
            self.__write_bytes(byte)
            self.__stop()
        except ConnectionError as err:
            print(err)


    """
    @brief Read one byte from an I2C device
    
    @param addr [in] I2C address to read from
    @param off [in] register to start reading from

    @return byte: data read from the I2C device
    """
    def read_byte_data(self, addr, off):
        rval = None
        try:
            self.__start()
            self.__write_bytes(addr << 1)
            self.__write_bytes(off)
            self.__stop()
            self.__start()
            self.__write_bytes((addr << 1) | 1)
            rval = self.__read_bytes()
            rval = rval[0]
            self.__stop()
        except ConnectionError as err:
            print(err)
        return rval


    """
    @brief Write up to 32 bytes to an I2C device
    
    @param addr [in] I2C address to read from
    @param off [in] register to start reading from
    @param data [in] array of bytes to write

    @return None
    """
    def write_i2c_block_data(self, addr, off, data):
        try:
            self.__start()
            self.__write_bytes(addr << 1)
            if off is not None:
                self.__write_bytes(off)
            self.__write_bytes(data)
            self.__stop()
        except ConnectionError as err:
            print(err)


    """
    @brief Read up to 32 bytes from an I2C device
    
    @param addr [in] I2C address to read from
    @param off [in] register to start reading from
    @param length [in] number of bytes to read, <=32

    @return array: bytes read from bus
    """
    def read_i2c_block_data(self, addr, off, length):
        rval = None
        try:
            self.__start()
            self.__write_bytes(addr << 1)
            self.__write_bytes(off)
            self.__stop()
            self.__start()
            self.__write_bytes((addr << 1) | 1)
            rval = self.__read_bytes(length)
            self.__stop()
        except ConnectionError as err:
            print(err)
        return rval


"""
@brief Perform a simple scan for devices attached to the I2C bus.

@param i2c [in] CH341 device to use for I2C scanning

@return None
"""
def scan(i2c):
    results = []
    for i in range(250):
        r = i2c.detect(i)
        if r: results += [i]
    print("Responses from i2c devices at: ", [hex(a) for a in results])


if __name__ == "__main__":
    try:
        i2c = CH341()
        i2c.set_speed(100)
    except ConnectionError as err:
        print(err)

    scan(i2c)
