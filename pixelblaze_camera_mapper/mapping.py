#!/usr/bin/env python3
import time
import json
import sys
from typing import NamedTuple

import pixelblaze
from scipy.spatial import distance

import config
import camera


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


def set_brightness(pb, brightness):
    if brightness > 1:
        brightness = float(brightness / 100)
    pb.setBrightnessSlider(brightness)


def set_binary_pattern(num_bits, bit_sequence_index):
    pixel_array = [0] * config.NUM_LEDS

    for i in range(config.NUM_LEDS):
        binary_number_string = bin(i)[2:].zfill(num_bits)
        bit_at_index = binary_number_string[num_bits - 1 - bit_sequence_index]
        pixel_array[i] = bit_at_index

    return pixel_array


def show_calibration_pixels(pb, capture_multiple_pixels):
    if capture_multiple_pixels:
        print("Lighting calibration pixels")
        pb.setActivePatternByName("binary mapping")
        calibration_array = [1] * (int)(config.NUM_LEDS)
        pb.setActiveVariables({"pixels_to_light": calibration_array})
    else:
        print("Blinking calibration pixel")
        pb.setActivePatternByName("blink pixel")
        pb.setActiveVariables({"pixel_to_light": 1})


def all_pixels_off(pb):
    pb.setActivePatternByName("pixel index")
    pb.setActiveVariables({"pixel_to_light": -1})


def get_num_bits_for_num_leds():
    return int(config.NUM_LEDS).bit_length()


class LedWithFramesSeen(NamedTuple):
    coordinate: list
    frames_seen: dict


def find_known_leds_in_frame(all_known_leds, leds_in_frame, frame_index):
    # Handle case where no LEDs were found this frame
    if len(leds_in_frame) < 1:
        for led in all_known_leds:
            led.frames_seen[frame_index] = False
        return

    for led in all_known_leds:
        # LED center might not be exactly the same, so let's find which known LED is close
        distance_array = distance.cdist([led.coordinate], leds_in_frame, "euclidean")
        closest_pixel_index = distance_array.argmin()
        if distance_array[0][closest_pixel_index] < 2:
            led.frames_seen[frame_index] = True
        else:
            led.frames_seen[frame_index] = False


def capture_locations_of_leds_for_led_string_state(
    pb, light_pattern, vc, threshold, background_image, frame_number
):
    # pb.setActivePatternByName("binary mapping")
    pb.setActiveVariables({"pixels_to_light": light_pattern})
    time.sleep(0.5)
    frame = camera.get_frame(vc, background_image)
    current_locations, _, _ = camera.get_led_positions(
        frame,
        threshold,
        find_multiple_leds=True,
        save_image=True,
        minimum_dimension=1,
        frame_number=frame_number,
    )
    return current_locations


def get_led_index_from_frames_seen(binary_dict):
    binary_array = [str(0)] * get_num_bits_for_num_leds()
    for key, value in binary_dict.items():
        if value:
            binary_array[key] = str(1)
        else:
            binary_array[key] = str(0)

    binary_array_little_endian = reversed(binary_array)
    binary_string = "".join(binary_array_little_endian)
    decimal_integer = int(binary_string, 2)
    return decimal_integer


def map_pixels_binary(pb):
    threshold, background_image = camera.launch_calibration_window(
        config.CAMERA_ID,
        pb,
        find_multiple_pixels=True,
        subtract_background=config.SUBTRACT_BACKGROUND,
    )

    vc = camera.open_camera(config.CAMERA_ID)
    pb.setActivePatternByName("binary mapping")
    print("Starting LED location capture")

    # Find locations of all pixels first
    turn_all_pixels_on = [1] * config.NUM_LEDS
    locations_of_all_leds = capture_locations_of_leds_for_led_string_state(
        pb=pb,
        light_pattern=turn_all_pixels_on,
        vc=vc,
        threshold=threshold,
        background_image=background_image,
        frame_number=9999,
    )

    # Initialize list of known LED positions
    all_known_leds = []
    for led in locations_of_all_leds:
        new_led_def = LedWithFramesSeen(coordinate=led, frames_seen={})
        all_known_leds.append(new_led_def)

    # Capture each frame of LEDs in the binary pattern
    num_bits = get_num_bits_for_num_leds()
    for i in range(num_bits):
        # Turn on pixels in the pattern, find their coordinates
        pixel_array = set_binary_pattern(num_bits, i)
        leds_found_in_frame = capture_locations_of_leds_for_led_string_state(
            pb=pb,
            light_pattern=pixel_array,
            vc=vc,
            threshold=threshold,
            background_image=background_image,
            frame_number=i,
        )
        # Reconcile what we found in this frame with the LEDs we know about
        find_known_leds_in_frame(all_known_leds, leds_found_in_frame, i)

    print("Done capturing LED locations with camera")
    vc.release()

    print("Turning all LED locations into an LED array")
    led_array = [
        [-1] * 2 for i in range(config.NUM_LEDS)
    ]  # Initialize array with all [-1,-1]
    for led in all_known_leds:
        pixel_index = get_led_index_from_frames_seen(led.frames_seen)
        led_array[pixel_index] = led.coordinate

    return ignore_empty_pixels(led_array)


def map_pixels_linearly(pb):
    threshold, background_image = camera.launch_calibration_window(
        config.CAMERA_ID, pb, subtract_background=config.SUBTRACT_BACKGROUND
    )

    locations = []
    pb.setActivePatternByName("pixel index")
    vc = camera.open_camera(config.CAMERA_ID)

    print("Starting LED location capture")
    for i in range(config.NUM_LEDS):
        pb.setActiveVariables({"pixel_to_light": i})
        time.sleep(0.2)

        frame = camera.get_frame(vc, background_image)
        location, _, _ = camera.get_led_positions(
            frame,
            threshold,
            find_multiple_leds=False,
            save_image=True,
            minimum_dimension=0,
            frame_number=i,
        )

        # print("Found LED at ", location)
        locations.append(location)

    print("Finishing LED location capture")
    vc.release()
    return ignore_empty_pixels(locations)


def main_program():
    pb = pixelblaze.Pixelblaze(config.PIXELBLAZE_IP)
    config.NUM_LEDS = pb.getPixelCount()
    print("Number of pixels to calibrate: ", config.NUM_LEDS)

    original_brightness = pb.getBrightnessSlider()

    pixelmap = None
    match config.MAPPING_METHOD:
        case config.MappingMethod.LINEAR:
            pixelmap = map_pixels_linearly(pb)
        case config.MappingMethod.BINARY:
            pixelmap = map_pixels_binary(pb)

    if pixelmap is None:
        print("No pixels found")
        sys.exit()

    print("Pixelblaze map coordinates generated: ")
    print(pixelmap)

    print("Setting coordinates as pixel map")
    pb.setMapCoordinates(pixelmap)
    pb.wsSendJson({"mapperFit": 0})

    pb.setActivePatternByName("Half and Half with missing pixels")
    pb.setBrightnessSlider(original_brightness)

    print("Saving generated data to out/ folder")
    camera.generate_output_image(config.CAMERA_ID, pixelmap, "pixelmap")
    with open("out/pixelmap.json", "w", encoding="utf8") as outfile:
        json.dump(pixelmap, outfile)


if __name__ == "__main__":
    main_program()
