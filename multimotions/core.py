import os
import time

import keyboard
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyautogui
from pynput.mouse import Listener
from scipy.ndimage import gaussian_filter
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


class WebPageCapture:
	def __init__(self, chrome_driver_path):
		self.chrome_driver_path = chrome_driver_path
	
	def capture_screenshot(self, url, output_path):
		chrome_options = Options()
		chrome_options.add_argument("--headless")
		chrome_options.add_argument("--window-size=1920x1080")
		chrome_options.add_argument("--hide-scrollbars")
		driver = webdriver.Chrome(self.chrome_driver_path, options=chrome_options)
		driver.set_page_load_timeout(60)  # set the page load timeout
		driver.get(url)
		# Set the width and height of the browser window to the size of the whole document
		total_width = driver.execute_script("return document.body.offsetWidth")
		total_height = driver.execute_script("return document.body.parentNode.scrollHeight")
		driver.set_window_size(total_width, total_height)
		screenshot = driver.get_screenshot_as_png()
		driver.quit()
		with open(output_path, 'wb') as file:
			file.write(screenshot)
	
	def capture_html(self, url, output_path):
		chrome_options = Options()
		chrome_options.add_argument("--headless")
		chrome_options.add_argument("--window-size=1920x1080")
		chrome_options.add_argument("--hide-scrollbars")
		driver = webdriver.Chrome(self.chrome_driver_path, options=chrome_options)
		driver.get(url)
		with open(output_path, 'w', encoding='utf-8') as file:
			file.write(driver.page_source)
		driver.quit()


class DataProcessor:
	def __init__(self, web_data_path, imotion_data_path, output_dir):
		self.web_data_path = web_data_path
		self.imotion_data_path = imotion_data_path
		self.output_dir = output_dir
		self.capture_handler = WebPageCapture(chrome_driver_path="path/to/chromedriver")
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

	def process_imotion_data(self):
		imotion_data = pd.read_csv(self.imotion_data_path)
		# Process the data as needed
		gaze_data = imotion_data[1:-2] 
		gaze_data = gaze_data.loc[~(gaze_data["ET_GazeRightx"]==-1)].reset_index(drop=True)
		gaze_data = gaze_data[["Timestamp","Anger","Fear","Joy","Sadness","Surprise",
						"Engagement","Confusion","Neutral","ET_GazeRightx","ET_GazeLeftx","ET_GazeLefty",
						"ET_GazeRighty"]]
		# Convert the "Timestamp" column to datetime format with milliseconds
		gaze_data['Timestamp'] = pd.to_datetime(gaze_data['Timestamp'], unit='ms', utc=True)

		# Convert the datetime format to string with milliseconds
		gaze_data['Timestamp'] = gaze_data['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S.%f')
		eye_tracking_data= gaze_data.copy()
		return eye_tracking_data
	
	def merge_web_and_imotion_data(self):
		web_data = pd.read_csv(self.web_data_path)
		eye_tracking_data = self.process_imotion_data()
		# Make sure the timestamps are in datetime format
		web_data['Time (UTC)'] = pd.to_datetime(web_data['Time (UTC)'])
		eye_tracking_data['Timestamp'] = pd.to_datetime(eye_tracking_data['Timestamp'])

		# Calculate the time difference for the 'eye_tracking_data' from its start
		eye_tracking_data['Time From Start'] = eye_tracking_data['Timestamp'] - eye_tracking_data['Timestamp'].iloc[0]

		# Apply this difference to the 'web_data' timestamps
		eye_tracking_data['Aligned Timestamp'] = web_data['Time (UTC)'].iloc[0] + eye_tracking_data['Time From Start']
		# If you don't need the original timestamps or the 'Time From Start' in your final dataframe, you can drop them
		eye_tracking_data.drop(['Timestamp', 'Time From Start'], axis=1, inplace=True)

		# Make the 'Aligned Timestamp' the index of 'eye_tracking_data'
		eye_tracking_data.set_index('Aligned Timestamp', inplace=True)

		# Make 'Time (UTC)' the index of 'web_data'
		web_data.set_index('Time (UTC)', inplace=True)

		# Now merge both dataframes on nearest matching time
		merged_data = pd.merge_asof(web_data, eye_tracking_data, left_index=True, right_index=True, direction='nearest')

		merged_data.reset_index(inplace=True)
		
		return merged_data

	def process_data(self):

		merged_data = self.merge_web_and_imotion_data()
		 # **************************** Merged Data pre-processing ********************************************************
		merged_data['ET_GazeRightx'].interpolate(method='linear', inplace=True)
		merged_data['ET_GazeLeftx'].interpolate(method='linear', inplace=True)
		merged_data['ET_GazeLefty'].interpolate(method='linear', inplace=True)
		merged_data['ET_GazeRighty'].interpolate(method='linear', inplace=True)
		merged_data = merged_data.ffill() # Forward fill
		merged_data = merged_data.bfill() # Backward fill

		# Calculate average gaze position
		merged_data['MeanGazeX'] = merged_data[['ET_GazeRightx', 'ET_GazeLeftx']].mean(axis=1)
		merged_data['MeanGazeY'] = merged_data[['ET_GazeRighty', 'ET_GazeLefty']].mean(axis=1)
		merged_data.isnull().sum() # check the null values

		# get a dictionary for the split based on the URL
		data_dict = {url: df for url, df in merged_data.groupby('URL')}

		# Iterate over the dictionary and save each DataFrame as a separate CSV file
		for url, df in data_dict.items():
			# Create a valid file name from the URL
			filename = url.replace('https://', '').replace('/', '_') + '.csv'
			
			

