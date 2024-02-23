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
from selenium.common.exceptions import TimeoutException
from PIL import Image
from io import BytesIO
from scipy.stats import gaussian_kde


class WebPageCapture:
	def __init__(self, chrome_driver_path):
		self.chrome_driver_path = chrome_driver_path
	
	def capture_screenshot(self, url):
		chrome_options = Options()
		chrome_options.add_argument("--headless")
		chrome_options.add_argument("--window-size=1920x1080")
		chrome_options.add_argument("--hide-scrollbars")
		driver = webdriver.Chrome(self.chrome_driver_path, options=chrome_options)
		driver.set_page_load_timeout(60)  # set the page load timeout
		
		for _ in range(5):  # Retry up to 5 times
			try:
				start_time = time.time()
				driver.get(url)
				end_time = time.time()
				print(f"Time taken to load {url}: {end_time - start_time} seconds")
				break
			except TimeoutException:
							print("Loading took too much time, retrying...")
		# Set the width and height of the browser window to the size of the whole document
		total_width = driver.execute_script("return document.body.offsetWidth")
		total_height = driver.execute_script("return document.body.parentNode.scrollHeight")
		driver.set_window_size(total_width, total_height)
		screenshot_bytes = driver.get_screenshot_as_png()
		# Optionally, convert bytes to Image for manipulation or viewing
		screenshot_img = Image.open(BytesIO(screenshot_bytes))
		driver.quit()
		return screenshot_img
		
	
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
		self.output_data = pd.DataFrame(columns=['URL', 'Image_Path'])
		self.web_data = pd.read_csv(self.web_data_path,  skiprows=1, names=['Time (UTC)', 
							'Event', 'Scroll Position', 'Scroll Percentage', 'Mouse X', 'Mouse Y','URL'])
		# Get the unique URLs from the data
		self.unique_urls = self.web_data["URL"].unique()
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
		self.eye_tracking_data= gaze_data.copy()

	def process_web_data(self):
		# Replace NaN with 0 only at the beginning of each url sequence
		self.web_data.reset_index(drop=True, inplace=True)
		self.web_data['Scroll Percentage'] = self.web_data.groupby((self.web_data['URL'] != self.web_data['URL'].shift()).cumsum())['Scroll Percentage'].apply(lambda group: group.fillna(0, limit=1)).reset_index(drop=True)

		# Fill other NaN values (not at the start of a sequence) with the last valid observation forward to next valid
		self.web_data['Scroll Percentage'].fillna(method='ffill', inplace=True)

		# fill the null for the web data 
		self.web_data['Scroll Position'].fillna(method='ffill', inplace=True)
		self.web_data['Scroll Position'].fillna(method='bfill', inplace=True)
		self.web_data['Mouse X'].fillna(method='ffill', inplace=True)
		self.web_data['Mouse X'].fillna(method='bfill', inplace=True)
		self.web_data['Mouse Y'].fillna(method='ffill', inplace=True)
		self.web_data['Mouse Y'].fillna(method='bfill', inplace=True)

	
	def merge_web_and_imotion_data(self):
		
		# Make sure the timestamps are in datetime format
		self.web_data['Time (UTC)'] = pd.to_datetime(self.web_data['Time (UTC)'])
		self.eye_tracking_data['Timestamp'] = pd.to_datetime(self.eye_tracking_data['Timestamp'])

		# Calculate the time difference for the 'eye_tracking_data' from its start
		self.eye_tracking_data['Time From Start'] = self.eye_tracking_data['Timestamp'] - self.eye_tracking_data['Timestamp'].iloc[0]

		# Apply this difference to the 'web_data' timestamps
		self.eye_tracking_data['Aligned Timestamp'] = self.web_data['Time (UTC)'].iloc[0] + self.eye_tracking_data['Time From Start']
		# If you don't need the original timestamps or the 'Time From Start' in your final dataframe, you can drop them
		self.eye_tracking_data.drop(['Timestamp', 'Time From Start'], axis=1, inplace=True)

		# Make the 'Aligned Timestamp' the index of 'eye_tracking_data'
		self.eye_tracking_data.set_index('Aligned Timestamp', inplace=True)

		# Make 'Time (UTC)' the index of 'web_data'
		self.web_data.set_index('Time (UTC)', inplace=True)

		# Now merge both dataframes on nearest matching time
		self.merged_data = pd.merge_asof(self.web_data, self.eye_tracking_data, left_index=True, right_index=True, direction='nearest')

		self.merged_data.reset_index(inplace=True)

	def process_data(self):

		# Assuming `existing_screenshots` is a dictionary storing existing screenshots
		# Key: URL, Value: Screenshot Image object or byte array
		existing_screenshots = {}

		# Assuming `output_data` is a pandas DataFrame initialized somewhere above this code
		# Assuming `web_data` is a pandas DataFrame containing URLs and their corresponding image data

		# Dictionary to store the screenshots for the current session
		current_screenshots = {}
		# Iterate over the dictionary and save each DataFrame as a separate CSV file
		for url in self.unique_urls:

			screenshot_exists = url in existing_screenshots

			if screenshot_exists:
			# Use the existing screenshot from the dictionary
				current_screenshots[url] = existing_screenshots[url]
				print(f"Screenshot already exists for: {url}")
			else:
				print("Screenshot does not exist, loading the page...")
				# Navigate to the webpage
				# call the instance of the WebPageCapture class
				screenshot_img= self.capture_handler.capture_screenshot(url)
				# Store the screenshot in the current session dictionary
				current_screenshots[url] = screenshot_img
		# Update the data frames accordingly
		for url, img in current_screenshots.items():
			# Here you might want to convert img (PIL Image) to a format suitable for your DataFrame or application needs
			# For demonstration, let's assume we're storing the image in a byte array format
			img_byte_array = BytesIO()
			img.save(img_byte_array, format='PNG')
			img_bytes = img_byte_array.getvalue()

			# Add or update the data frame with the URL and the screenshot data
			if url in self.output_data['URL'].values:
				self.output_data.loc[self.output_data['URL'] == url, 'Image_Data'] = [img_bytes]
				self.web_data.loc[self.web_data['URL'] == url, 'Image_Data'] = [img_bytes]
			else:
				new_row = pd.DataFrame([{'URL': url, 'Image_Data': img_bytes}])
				self.output_data = pd.concat([self.output_data, new_row], ignore_index=True)
				self.web_data = pd.concat([self.web_data, new_row], ignore_index=True)
		
		self.process_merged_data()
		self.process_imotion_data()
		self.process_merged_data()
	
	
	def process_merged_data(self):
		self.merge_web_and_imotion_data()
		 # **************************** Merged Data pre-processing ********************************************************
		self.merged_data['ET_GazeRightx'].interpolate(method='linear', inplace=True)
		self.merged_data['ET_GazeLeftx'].interpolate(method='linear', inplace=True)
		self.merged_data['ET_GazeLefty'].interpolate(method='linear', inplace=True)
		self.merged_data['ET_GazeRighty'].interpolate(method='linear', inplace=True)
		self.merged_data = self.merged_data.ffill() # Forward fill
		self.merged_data = self.merged_data.bfill() # Backward fill

		# Calculate average gaze position
		self.merged_data['MeanGazeX'] = self.merged_data[['ET_GazeRightx', 'ET_GazeLeftx']].mean(axis=1)
		self.merged_data['MeanGazeY'] = self.merged_data[['ET_GazeRighty', 'ET_GazeLefty']].mean(axis=1)
		self.merged_data.isnull().sum() # check the null values
	
	def split_data(self):
		# Split the data into different sections based on the URL
		
		self.split_data = self.merged_data.groupby('URL')
		# Iterate over the groups and save each group as a separate CSV file
		url_dataframes=[]
		for name, group in self.split_data:
			# Save each group as a list of dataframes
			url_dataframes.append(group)
		return url_dataframes
			


	def plot_heatmap(self, data):
		# Get the unique image path from the dataframe
		img_path = data['Image_Path'].unique()[0]

		# Load screenshot as image
		img = Image.open(img_path)
		img_width, img_height = img.size
		
		# Calculate the normalized x and y coordinates
		P = data['Scroll Percentage'] / 100
		x = data['MeanGazeX']
		y = abs(data['MeanGazeY']) + (P * img_height)
		

		# Compute the point densities
		xy = np.vstack([x, y])
		z = gaussian_kde(xy)(xy)

		# Create the plot
		fig, ax = plt.subplots()
		ax.imshow(img, extent=[0, img_width, img_height, 0])

		# scatter the data and set the parameters 
		sc= ax.scatter(
		x, y, 
		s=500,                 # size of markers
		c=z,                   # color based on densities
		cmap='RdYlGn_r',       # colormap from red to green
		alpha=0.05,            # transparency
		marker='o',            # marker shape
		# edgecolors='black',  # edge color of markers
		linewidths=1.5         # edge line width
		)
	 	# Add a colorbar at the top with horizontal orientation
		# cbar = fig.colorbar(sc, cax=cbar_ax_top, orientation='horizontal')
		ax.set_xlim(x.min(), img_width)
		ax.set_ylim(img_height, 0)
		ax.axis('off')

		# Remove the boundries  
		plt.tight_layout()
		plt.subplots_adjust(top=1, bottom=0, right=1, left=0, hspace=0, wspace=0)
		plt.gca().set_axis_off()
		plt.gca().xaxis.set_major_locator(plt.NullLocator())
		plt.gca().yaxis.set_major_locator(plt.NullLocator())
		#return the plot
		return fig
	
	def create_heatmap(self):
		images = self.heatmaps_plotting()
		images_per_row=5
		num_images = len(images)
		num_rows = (num_images + images_per_row - 1) // images_per_row  # Calculate the number of rows needed

		# Create a figure with subplots in a grid
		fig, axes = plt.subplots(num_rows, images_per_row, figsize=(20, num_rows * 4))
		
		# Flatten axes array for easy iteration, in case of a single row or column
		if num_rows == 1:
			axes = np.array([axes])
		axes = axes.flatten()

		for ax, img in zip(axes, images):
			# Check if the image is a byte array, then convert it to a PIL Image
			if isinstance(img, bytes):
				img = Image.open(BytesIO(img))

			# Display the image
			ax.imshow(img)
			ax.axis('off')  # Hide the axes ticks

		# Hide any unused subplot axes if the number of images is not a perfect multiple of `images_per_row`
		for ax in axes[num_images:]:
			ax.axis('off')

		plt.tight_layout()
		plt.show()

	def heatmaps_plotting(self):
		# Split the data into different sections based on the URL
		url_dataframes = self.split_data()
		# Initialize an empty list to store all output 
		outputs=[]
		# Iterate over the groups and save each group as a separate CSV file
		for data in url_dataframes:
			outputs.extend(self.plot_heatmap(data))
		return outputs

	
		
			
			

