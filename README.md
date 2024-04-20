This is a project to read the GPS coordinates from a Waveshare GPS HAT, and read four analogue channels at the same frequency, and save their values with the coordinates, to a file.

The program runs on a Raspberry Pi 3, though it will probably also run on other platforms.
It sets the GPS chip in to 10Hz mode, and logs coordinates at 10Hz, to file.
If the vehicle stops, the recording stops, and automatically restarts when the vehicle restarts.

The Waveshare board that I used is shown in more detail here.
https://www.waveshare.com/wiki/GSM/GPRS/GNSS_HAT
It uses the SIM868 modem, which is controlled by sending AT Codes to it over serial.

More details of the project can be found on my Blog here.
https://www.zetecinside.com/xr2/rpi_project2.shtml
