#!/usr/bin/env python3
import time
import json
from pixelblaze import *
from pixelblaze_camera_mapper import camera


PIXELBLAZE_IP = "192.168.2.73"
CAMERA_ID = 0


def ignore_empty_pixels(positions):
    default_x = min([i[0] for i in positions if i[0] > 0])
    default_y = min([i[1] for i in positions if i[1] > 0])
    positions_3d = []
    for [x, y] in positions:
        if x == -1 and y == -1:
            positions_3d.append([default_x, default_y, 1])
        else:
            positions_3d.append([x, y, 0])
    return positions_3d


def run_mapping_task(threshold, pb, num_leds, brightness):
    locations = []
    vc = camera.open_camera(CAMERA_ID)

    print(
        "Starting LED location capture with LED brightness "
        + str(brightness)
        + " and threshold "
        + str(threshold)
    )
    for i in range(num_leds):
        pb.setActiveVariables({"pixel_to_light": i})
        time.sleep(0.2)

        frame = camera.get_frame(vc)
        location, _, _ = camera.get_led_position(
            frame, threshold, save_image=True, minimum_dimension=0
        )

        #print("Found LED at ", location)
        locations.append(location)

    print("Finishing LED location capture")
    vc.release()
    return locations


def main():
    pb = Pixelblaze(PIXELBLAZE_IP)
    num_pixels = pb.getPixelCount()
    print("Number of pixels to calibrate: ", num_pixels)

    original_brightness = pb.getBrightnessSlider()

    print("Blinking calibration pixel")
    pb.setActivePatternByName("blink pixel")
    pb.setActiveVariables({"pixel_to_light": 1})

    brightness, threshold = camera.launch_calibration_window(CAMERA_ID, pb)

    pb.setActivePatternByName("pixel index")
    locations = run_mapping_task(threshold, pb, num_pixels, brightness)
    # print("Found pixels at:")
    # print(locations)

    pixelmap = ignore_empty_pixels(locations)
    print("Pixelblaze map coordinates generated: ")
    print(pixelmap)

    print("Saving generated data to out/ folder")
    camera.generate_output_image(CAMERA_ID, locations, "pixelmap")
    with open("out/pixelmap.json", "w", encoding="utf8") as outfile:
        json.dump(pixelmap, outfile)

    print("Setting coordinates as pixel map")
    pb.setMapCoordinates(pixelmap)
    pb.wsSendJson({"mapperFit":0})

    pb.setActivePatternByName("Half and Half with missing pixels")
    pb.setBrightnessSlider(original_brightness)


if __name__ == "__main__":
    main()
