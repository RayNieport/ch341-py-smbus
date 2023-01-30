*Archived because I no longer have access to the device.*

# CH341 I2C Python Library

> Read and write to the I2C bus via the CH341 USB Bridge Controller in I2C/MEM/EPP mode.

## What does this library do?
Essentially, this library sends a series of USB commands to the CH341 to control I2C functionality. It provides an API that is mostly compatible with [smbus2](https://pypi.org/project/smbus2/), although it does not include the `i2c_rdwr` function for transmitting bulk data. It's been tested on both CH341A and CH341T_V3 variants, using I2C Master Mode. 

## Dependencies:
This library depends on [PyUSB](https://pypi.org/project/pyusb/), which itself depends on libusb. The easiest way to install libusb on Windows is to use [Zadig](https://zadig.akeo.ie/) (make sure to select the correct device). This may not be necessary on Linux systems, depending on your distribution. On Linux, you can also look into using [this driver](https://github.com/gschorcht/i2c-ch341-usb) to communicate with the CH341.

## More information:
While the CH341 is a relatively cheap USB to I2C solution, I found very little documentation or software support on the [manufacturer's website](http://www.wch-ic.com/products/CH341.html). Drivers are available, but I've been unable to find any API reference or directions for using the driver. Thanks to Karl Palsson, who made the CH341 USB commands accessible in [this repository](https://github.com/karlp/ch341-py2c). 
