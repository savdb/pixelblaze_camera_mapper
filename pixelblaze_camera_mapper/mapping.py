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


def set_binary_pattern(num_leds, num_bits, bit_sequence_index):
    pixel_array = [0] * num_leds

    for i in range(num_leds):
        binary_number_string = bin(i)[2:].zfill(num_bits)
        bit_at_index = binary_number_string[num_bits - 1 - bit_sequence_index]
        pixel_array[i] = bit_at_index

    return pixel_array


def run_binary_mapping_task(threshold, pb, num_leds):
    pb.setActivePatternByName("binary mapping")
    vc = camera.open_camera(CAMERA_ID)
    print("Starting LED location capture")
    num_bits = int(num_leds).bit_length()

    locations = []
    for i in range(num_bits):
        pixel_array = set_binary_pattern(num_leds, num_bits, i)
        pb.setActiveVariables({"pixels_to_light": pixel_array})
        time.sleep(0.5)
        frame = camera.get_frame(vc)
        current_locations, _, _ = camera.get_all_led_positions(
            frame, threshold, save_image=True, minimum_dimension=1
        )
        locations.append(current_locations)

    # TODO: Now that we have many arrays of coordinates, we need to reconcile the blobs
    # and locate the pixels based on their inferred id
    return locations


def map_pixels_binary():
    pb = Pixelblaze(PIXELBLAZE_IP)
    num_pixels = pb.getPixelCount()
    print("Number of pixels to calibrate: ", num_pixels)

    # original_brightness = pb.getBrightnessSlider()

    pb.setActivePatternByName("binary mapping")
    calibration_array = [1, 0] * (int)(num_pixels / 2)
    pb.setActiveVariables({"pixels_to_light": calibration_array})

    threshold = camera.launch_calibration_window(
        CAMERA_ID, pb, find_multiple_pixels=True
    )

    pixelmap = run_binary_mapping_task(threshold, pb, num_pixels)
    print(pixelmap)


def run_linear_mapping_task(threshold, pb, num_leds):
    locations = []

    pb.setActivePatternByName("pixel index")
    vc = camera.open_camera(CAMERA_ID)

    print("Starting LED location capture")
    for i in range(num_leds):
        pb.setActiveVariables({"pixel_to_light": i})
        time.sleep(0.2)

        frame = camera.get_frame(vc)
        location, _, _ = camera.get_led_position(
            frame, threshold, save_image=True, minimum_dimension=0
        )

        # print("Found LED at ", location)
        locations.append(location)

    print("Finishing LED location capture")
    vc.release()
    return ignore_empty_pixels(locations)


def map_pixels_linearly():
    pb = Pixelblaze(PIXELBLAZE_IP)
    num_pixels = pb.getPixelCount()
    print("Number of pixels to calibrate: ", num_pixels)

    original_brightness = pb.getBrightnessSlider()

    print("Blinking calibration pixel")
    pb.setActivePatternByName("blink pixel")
    pb.setActiveVariables({"pixel_to_light": 1})

    threshold = camera.launch_calibration_window(CAMERA_ID, pb)

    pixelmap = run_linear_mapping_task(threshold, pb, num_pixels)
    print("Pixelblaze map coordinates generated: ")
    print(pixelmap)

    print("Setting coordinates as pixel map")
    pb.setMapCoordinates(pixelmap)
    pb.wsSendJson({"mapperFit": 0})

    pb.setActivePatternByName("Half and Half with missing pixels")
    pb.setBrightnessSlider(original_brightness)

    print("Saving generated data to out/ folder")
    camera.generate_output_image(CAMERA_ID, pixelmap, "pixelmap")
    with open("out/pixelmap.json", "w", encoding="utf8") as outfile:
        json.dump(pixelmap, outfile)


if __name__ == "__main__":
    map_pixels_linearly()
