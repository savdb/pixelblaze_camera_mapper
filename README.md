# Pixelblaze Camera Mapper

This project uses a camera to capture the location of addressable LEDs in 2d, and outputs a ledmap that can be used in Pixelblaze.

It communicates with pixelblaze via the Websocket API, then uses OpenCV to detect the coordinates of their location in the camera image.

This program was written to run on a computer with a webcam pointing at the LEDs, on the same network as the Pixelblaze instance so it can communicate wirelessly.

## Setup steps in Pixelblaze

1. Download the patterns from the `pixelblaze_patterns` folder in this repository and upload them to your Pixelblaze instance.

## Setup steps on your computer

1. Set your Pixelblaze IP address at the top of `config.py`
2. Install dependencies listed in `pyproject.toml`. You can use [poetry](https://python-poetry.org/) to do this or install them yourself.
3. In python, run `mapping.py`.
4. The Camera calibration screen will open. If openCV is using a different camera than the one you expect, kill the program and choose a different camera id at the top of `config.py` until you see the correct one.

## Running the mapping program

1. Position your camera so that it can see as many of your LEDs as possible. LEDs the camera can't see will be skipped in the generated ledmap. See the "Skipped LEDs" section below.
2. While in the calibration screen, one LED will blink. Change the threshold until the LED screen shows all black when the LED is off, and shows a small red box around the LED when the LED is on. Adjust the LED brightness if necessary to get an accurate size around the LED. If you're having trouble isolating just the LED in the camera calibration, try running in a dark room, with a non-reflective neutral background.  If your camera is auto-adjusting the brightness/contrast in real-time, hopefully you can turn that off. Good luck.
3. Once you're happy with the calibration, press the `Esc` key to close the calibration window. The LED mapping will begin automatically as soon as the calibration window is closed.
4. The program will flash each LED in order, up to the number of LEDs that Pixelblaze says you have.  As it flashes each LED, it captures a screenshot of each one to the `out/` directory.
5. The program will save your `pixelmap.json` file to `out/` and also create an image with all the LEDs marked so you can compare the output.
6. After creating the ledmap json file, the program will upload the map to Pixelblaze.

## Skipped LEDs

Sometimes this mapper can't find a location for a given LED index (the camera couldn't see it), we need to skip them in the pixelmap somehow.  This tool creates a 3d map that is intended to be treated as a 2d map. Pixels with known positions have z=0, and pixels with unknown positions have z=1. In your 2D patterns, use `render3D` and then set any pixel where `z!= 0` to be off.

Example:

```javascript
export function render3D(index,x,y,z) {
  if(z != 0){
    rgb(0,0,0)
  }
  else {
    rgb(0,1,0)
  }
}
```
