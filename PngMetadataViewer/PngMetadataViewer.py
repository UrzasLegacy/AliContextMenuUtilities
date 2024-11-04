import json
import sys
import tkinter as tk
import logging
import os
import base64
from PIL import Image
from PIL.ExifTags import TAGS

log_file_path = os.path.splitext(os.path.abspath(__file__))[0] + ".log"
logging.basicConfig(
    level=logging.DEBUG,  # Set the minimum log level
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Format for log messages
    datefmt='%Y-%m-%d %H:%M:%S',  # Format for timestamps
    handlers=[
        logging.FileHandler(log_file_path)  # Output logs to a file
    ]
)
logger = logging.getLogger(__name__)
logger.propagate = False


def context_menu_execute(file_path):
	file_name = os.path.basename(file_path)
	out_data = [file_name]
	try:
		extracted_data = extract_png_metadata(file_path)
		if extracted_data == "No metadata found.":
			tkstuff("No metadata found","No metadata found","No metadata found","No metadata found")
			return
		for data in extracted_data:
			if isinstance(data,str):
				corrected_json_string = data.replace("'", '"')
				try:
					data_dict = json.loads(corrected_json_string)
					json_string = json.dumps(data_dict,indent=0).strip("{} \n")
				except Exception as e:
					json_string = data
					logging.error(f"data: {data}\ncorrected data: {corrected_json_string}", exc_info=True)
			elif isinstance(data,dict):
				json_string = json.dumps(data,indent=0)#.strip("{} \n")
			else:
				try:
					json_string = "No metadata found" if data is None else f"Metadata wasn't string or dict! Attempting string conversion: {data}"
				except Exception as e:
					logging.error(f"data: {data}", exc_info=True)
					json_string = f"Metadata wasn't string or dict and string conversion on metadata field failed"
			out_data.append(json_string)
	except:
		out_data = []
		extracted_data = extract_jpg_metadata(file_path)
		if extracted_data == "No metadata found.":
			tkstuff("No metadata found","No metadata found","No metadata found","No metadata found")
			return
		for data in extracted_data:
			if isinstance(data,str):
				corrected_json_string = data.replace("'", '"')
				try:
					data_dict = json.loads(corrected_json_string)
					json_string = json.dumps(data_dict,indent=0).strip("{} \n")
				except Exception as e:
					json_string = data
					logging.error(f"data: {data}\ncorrected data: {corrected_json_string}", exc_info=True)
			elif isinstance(data,dict):
				json_string = json.dumps(data,indent=0)#.strip("{} \n")
			else:
				try:
					json_string = "No metadata found" if data is None else f"Metadata wasn't string or dict! Attempting string conversion: {data}"
				except Exception as e:
					logging.error(f"data: {data}", exc_info=True)
					json_string = f"Metadata wasn't string or dict and string conversion on metadata field failed"
			out_data.append(json_string)
		
	tkstuff(*out_data)

	
def tkstuff(file_name="",ali_metadata="", a1111_metadata="", extra_metadata="", exif_data=""):
	root = tk.Tk()
	root.title(file_name)
	
	def close_window(event=None):
		root.destroy()

	root.bind('<Escape>', close_window)
	height = 400
	width = 800
	root.geometry(f"{width}x{height}")
	root.grid_rowconfigure(0, weight=1)
	root.grid_columnconfigure(0, weight=1)
	root.grid_columnconfigure(1, weight=0)
	text_widget = tk.Text(root, wrap='word')
	#text_widget.insert(tk.END, f"{pnginfo}")
	#text_widget.insert(tk.END, f"\n\n{exif_data}")
	text_widget.insert(tk.END, f"{extra_metadata}\n\n\nAli:\n{ali_metadata}\n\nA1111:\n{a1111_metadata}")
	
	text_widget.insert(tk.END, f"\n\n{exif_data[:25000]}")

	# Schedule remaining text insertion after window is rendered
	text_widget.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
	scrollbar = tk.Scrollbar(root, orient=tk.VERTICAL, command=text_widget.yview)
	scrollbar.grid(row=0, column=1, sticky='ns')

	# Disable editing
	text_widget.config(state=tk.DISABLED)
	text_widget.config(yscrollcommand=scrollbar.set)

	root.mainloop()
	

def extract_png_metadata(file_path):
	with Image.open(file_path) as img:
		exif_data = img.info
		if not exif_data:
			return "No metadata found."

		ali_metadata = exif_data.get('ali_metadata')
		a1111_metadata = exif_data.get('parameters')
		extra_metadata = exif_data.get('extra_metadata')

		return ali_metadata, a1111_metadata, extra_metadata, exif_data


def extract_jpg_metadata(file_path):
	with Image.open(file_path) as img:
		exif_data = img._getexif()
		if not exif_data:
			return "No metadata found."
		else:
			exif = {}
			for tag, value in exif_data.items():
				tag_name = TAGS.get(tag, tag)
				if isinstance(value, bytes):
					value = base64.b64encode(value)
					value = base64.b64decode(value).decode('utf-8')
					metadata_without_prefix = value.replace('UNICODE', '')
					decoded_metadata = bytes(metadata_without_prefix, "utf-8").decode("unicode_escape")
					cleaned_metadata = decoded_metadata.replace('\u0000', '')
					value = cleaned_metadata
				exif[tag_name] = value
			logging.debug(f"jpg: {exif}")
			return {}, {}, {}, exif




if __name__ == "__main__":
	if len(sys.argv) > 1:
		file_path = sys.argv[1]
		context_menu_execute(file_path)
	else:
		print("No file path provided.")


