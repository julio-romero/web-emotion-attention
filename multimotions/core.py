import os
import time

import keyboard
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyautogui
from pynput.mouse import Listener
from scipy.ndimage import gaussian_filter


class DataProcessor:
    def __init__(self, web_data_path, imotion_data_path, output_dir):
        self.web_data_path = web_data_path
        self.imotion_data_path = imotion_data_path
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        self.screenshot_paths = []
        self.mouse_activity_files = []

    def take_screenshot(self, screen_number):
        screenshot_path = os.path.join(self.output_dir, f"screen_{screen_number}.png")
        screenshot = pyautogui.screenshot()
        screenshot.save(screenshot_path)
        print("Screenshot taken")
        self.screenshot_paths.append(screenshot_path)

    def capture_mouse_activity(self, screen_number):
        mouse_activity_path = os.path.join(
            self.output_dir, f"screen_{screen_number}.txt"
        )
        self.mouse_activity_files.append(mouse_activity_path)
        with open(mouse_activity_path, "w", encoding="utf-8") as file:

            def on_move(x, y):
                file.write(f"Mouse moved to x-{x}, y-{y}\n")

            def on_click(x, y, button, pressed):
                file.write(f"Mouse clicked at x-{x}, y-{y} with {button}\n")

            def on_scroll(x, y, dx, dy):
                file.write(f"Mouse scrolled at x-{x}, y-{y} with dx-{dx} dy-{dy}\n")
                return False  # Stops the listener

            with Listener(
                on_move=on_move, on_click=on_click, on_scroll=on_scroll
            ) as listener:
                listener.join()

    def start_monitoring(self, duration=5):
        end_time = time.time() + duration
        screen_number = 0
        while True:
            if time.time() >= end_time:
                screen_number += 1
                self.take_screenshot(screen_number)
                self.capture_mouse_activity(screen_number)
                end_time = time.time() + duration

            if keyboard.is_pressed("q"):
                print("Stopping monitoring")
                break

    def parse_mouse_actions_to_dataframe(self, activity_file):
        structured_data = []
        with open(activity_file, encoding="utf-8") as file:
            for line in file:
                action_details = {}
                parts = line.split(" ")
                action_type = (
                    "moved"
                    if "moved" in line
                    else "clicked"
                    if "clicked" in line
                    else "scrolled"
                )
                coords = [
                    coord.split("-")[1].replace(",", "")
                    for coord in parts
                    if "-" in coord
                ]
                x, y = [int(float(coord)) for coord in coords[:2]]

                action_details["action"] = action_type
                action_details["x"] = x
                action_details["y"] = y

                # Additional details for clicked and scrolled actions
                if action_type == "clicked" or action_type == "scrolled":
                    details = " ".join(parts[5:])
                    action_details["details"] = details.strip()

                structured_data.append(action_details)

        return pd.DataFrame(structured_data)

    def plot_data(self):
        for screenshot_path, activity_file in zip(
            self.screenshot_paths, self.mouse_activity_files
        ):
            df = self.parse_mouse_actions_to_dataframe(activity_file)

            img = plt.imread(screenshot_path)
            display_array = np.zeros(img.shape[:2])

            for index, row in df.iterrows():
                x, y = row["x"], row["y"]
                display_array[y, x] += 1

            plt.imshow(img, alpha=0.8)
            plt.axis("off")

            smoothed = gaussian_filter(display_array, sigma=50)
            plt.imshow(smoothed, cmap="jet", alpha=0.5)
            plt.show()  # Show the plot for each screenshot and activity pair
