from __future__ import annotations


import os
from functools import partial

import cv2 as cv

import mapping
import config


def do_nothing(_):
    pass


def change_brightness(brightness_value, pb=None):
    # print("Setting brightness to "+str(brightness_value)+"%")
    brightness_value = float(brightness_value / 100)
    mapping.set_brightness(pb, brightness_value)


def open_camera(camera_id):
    vc = cv.VideoCapture(camera_id)
    if not vc.isOpened():  # try to get the first frame
        print("Can't open camera")
        vc.release()
        cv.destroyAllWindows()
        exit()
    return vc


def launch_calibration_window(
    camera_id, pb, find_multiple_pixels=False, subtract_background=False
):
    window_name = "Camera Calibration"
    cv.namedWindow(window_name)
    cv.createTrackbar("Threshold", window_name, 230, 255, do_nothing)
    cv.createTrackbar(
        "LED_Brightness", window_name, 50, 100, partial(change_brightness, pb=pb)
    )

    vc = open_camera(camera_id)
    print("Calibration window is opened")

    if subtract_background:
        mapping.all_pixels_off(pb)
    else:
        mapping.show_calibration_pixels(pb, find_multiple_pixels)

    threshold = 230
    background_image_found = False
    background_image = None

    while True:
        success, frame = vc.read()
        if not success:
            print("Couldn't get frame, exiting")
            break

        if subtract_background and not background_image_found:
            background_image = frame.copy()
            mapping.show_calibration_pixels(pb, find_multiple_pixels)
            background_image_found = True

        if subtract_background:
            frame_without_background = cv.absdiff(background_image, frame)
            frame = frame_without_background

        threshold = cv.getTrackbarPos("Threshold", window_name)

        _, contour_image, gray_image = get_led_positions(
            frame, threshold, find_multiple_leds=find_multiple_pixels
        )

        gray_image = overlay_text(gray_image)
        cv.imshow(window_name, gray_image)
        cv.imshow("Detected LED", contour_image)

        # Wait for escape key
        key = cv.waitKey(20)
        if key == 27:  # exit on ESC
            break

    print("Destroying calibration windows")
    cv.destroyAllWindows()
    vc.release()
    return threshold, background_image


def overlay_text(image):
    image = cv.cvtColor(image, cv.COLOR_GRAY2RGB)
    return cv.putText(
        image,
        "Press Esc to exit calibration",
        (5, 50),
        cv.FONT_HERSHEY_SIMPLEX,
        fontScale=1,
        color=255,
        thickness=2,
    )


def create_threshold(grey_image, threshold):
    margin = 1 + threshold
    # threshold = int( maxVal * margin)
    threshold_value = margin

    _, threshold_image = cv.threshold(
        grey_image, threshold_value, 255, cv.THRESH_BINARY
    )
    return threshold_image


def create_erosion(image):
    erosion_size = config.EROSION_SIZE
    element = cv.getStructuringElement(cv.MORPH_ELLIPSE, (erosion_size, erosion_size))
    return cv.morphologyEx(image, cv.MORPH_OPEN, element)


def locate_led_in_image(threshold_image, minimum_dimension=3):
    minimum_dimension = 3

    edged_image = threshold_image.copy()
    contours, _ = cv.findContours(edged_image, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)

    if len(contours) > 0:
        biggest_contour = max(contours, key=cv.contourArea)
        x, y, w, h = cv.boundingRect(biggest_contour)

        if w >= minimum_dimension and h >= minimum_dimension:
            contour_image = cv.cvtColor(threshold_image, cv.COLOR_GRAY2RGB)
            cv.rectangle(contour_image, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cx = int(x + (w / 2))
            cy = int(y + (h / 2))
            return [cx, cy], contour_image

    return [-1, -1], edged_image  # Nothing found in this image


def locate_all_leds_in_image(threshold_image, minimum_dimension=3):
    minimum_dimension = 3

    edged_image = threshold_image.copy()
    contours, _ = cv.findContours(edged_image, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
    if not len(contours) > 0:
        return [], edged_image

    contour_image = cv.cvtColor(threshold_image, cv.COLOR_GRAY2RGB)
    contour_points = []
    for contour in contours:
        x, y, w, h = cv.boundingRect(contour)
        if w >= minimum_dimension and h >= minimum_dimension:
            cx = int(x + (w / 2))
            cy = int(y + (h / 2))
            cv.circle(contour_image, (cx, cy), 5, (0, 0, 255), 2)

            contour_points.append([cx, cy])

    # contour_image = cv.drawContours(contour_image, contours, -1, (255,0,0), 3)
    return contour_points, contour_image


def get_led_positions(
    frame,
    threshold,
    find_multiple_leds=False,
    save_image=False,
    minimum_dimension=3,
    frame_number=0,
):
    gray_image = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    threshold_image = create_threshold(gray_image, threshold)
    threshold_image = create_erosion(threshold_image)

    locations = None
    contour_image = None

    if find_multiple_leds:
        locations, contour_image = locate_all_leds_in_image(
            threshold_image, minimum_dimension
        )
    else:
        locations, contour_image = locate_led_in_image(
            threshold_image, minimum_dimension
        )

    if save_image:
        cv.imwrite("out/led" + str(frame_number) + ".png", contour_image)

    return locations, contour_image, gray_image


def draw_all_led_positions(locations, image):
    print("Drawing locations on image")

    # Put into grayscale, then back into color
    image = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
    image = cv.cvtColor(image, cv.COLOR_GRAY2RGB)

    for led_index, coordinates in enumerate(locations):
        coordinates = [coordinates[0], coordinates[1]]
        image = cv.circle(image, coordinates, radius=5, color=(255, 0, 0), thickness=2)
        image = cv.putText(
            image,
            str(led_index),
            coordinates,
            cv.FONT_HERSHEY_SIMPLEX,
            fontScale=1,
            color=255,
            thickness=2,
        )
    return image


def get_frame(vc, background_image=None):
    success, frame = vc.read()
    if not success:
        print("Couldn't get frame, exiting")
        return None
    # frame = cv.resize(frame, dsize=(75,75), interpolation=cv.INTER_CUBIC)

    if background_image is not None:
        frame_without_background = cv.absdiff(background_image, frame)
        frame = frame_without_background

    return frame


def generate_output_image(camera_id, locations, name):
    print("Creating output image")
    vc = cv.VideoCapture(camera_id)
    if not vc.isOpened():  # try to get the first frame
        print("Can't open camera")
        vc.release()
        exit()
    success, frame = vc.read()
    if not success:
        print("Couldn't get frame, exiting")
        return
    img = draw_all_led_positions(locations, frame)
    status = cv.imwrite("out/" + name + ".png", img)
    print("Image of LED locations saved: ", status)
    if status:
        os.system("start out/" + name + ".png")
