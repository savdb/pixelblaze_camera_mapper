#!/usr/bin/env python3
import time
import json
import sys

import pixelblaze

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
        calibration_array = [1, 0] * (int)(config.NUM_LEDS / 2)
        pb.setActiveVariables({"pixels_to_light": calibration_array})
    else:
        print("Blinking calibration pixel")
        pb.setActivePatternByName("blink pixel")
        pb.setActiveVariables({"pixel_to_light": 1})


def all_pixels_off(pb):
    pb.setActivePatternByName("pixel index")
    pb.setActiveVariables({"pixel_to_light": -1})


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
    num_bits = int(config.NUM_LEDS).bit_length()

    locations = []
    for i in range(num_bits):
        pixel_array = set_binary_pattern(num_bits, i)
        pb.setActiveVariables({"pixels_to_light": pixel_array})
        time.sleep(0.5)
        frame = camera.get_frame(vc, background_image)
        current_locations, _, _ = camera.get_led_positions(
            frame,
            threshold,
            find_multiple_leds=True,
            save_image=True,
            minimum_dimension=1,
            frame_number=i,
        )
        locations.append(current_locations)

    # TODO: Now that we have many arrays of coordinates, we need to reconcile the blobs
    # and locate the pixels based on their inferred id
    print(locations)
    print("Binary mapping not yet fully implemented, sorry.")

    return None


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
