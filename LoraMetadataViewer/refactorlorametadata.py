import os
import logging

log_file_path = os.path.splitext(os.path.abspath(__file__))[0] + ".log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.FileHandler(log_file_path)]
)
logger = logging.getLogger(__name__)

import sys
import json
import requests
import re
import hashlib
import concurrent.futures
import webbrowser
import numpy as np

import tkinter as tk
from tkinter import Text, Scrollbar, Canvas, Frame
from bs4 import BeautifulSoup
from PIL import Image,ImageTk
from io import BytesIO


API_URL_PREFIX = "https://civitai.com/api/v1/model-versions/by-hash/"
MODEL_PAGE_URL_PREFIX = "https://civitai.com/models/"
TEST_FILE_PATH = r"s:\SD_Archive\models\Lora\PONY\_Scoring\_Concept\Pony_XL_AllTheWayThrough_Concept.safetensors"

class SafetensorsException(Exception):
    def __init__(self, msg:str):
        self.msg = msg
        super().__init__(msg)

    @staticmethod
    def invalid_file(filename:str, whatiswrong:str):
        message = f"{filename} is not a valid .safetensors file: {whatiswrong}"
        return SafetensorsException(msg=message)

    def __str__(self):
        return self.msg



def extract_model_text_BROKEN(model_id):
    MODEL_PAGE_URL_PREFIX = "https://civitai.com/models/"
    model_url = MODEL_PAGE_URL_PREFIX + str(model_id)

    def safe_get(d, keys, default=None):
        for key in keys:
            try:
                d = d[key]
            except (KeyError, IndexError, TypeError):
                return default
        return d

    # Fetch the image from the URL
    response = requests.get(model_url)
    response.raise_for_status()  # Check if the request was successful
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, 'html.parser')
    script_tag = soup.find('script', type='application/json')
    if script_tag:
        try:

            data = json.loads(script_tag.string)
            keys = ["props", "pageProps", "trpcState", "json", "queries", -1, "state", "data", "description"]
            pull = safe_get(data, keys) #data["props"]["pageProps"]["trpcState"]["json"]["queries"][-1]["state"]["data"]["description"]
            soup = BeautifulSoup(pull, "html.parser")

            description_text= soup.get_text(separator="\n", strip=True).strip()
            return description_text
        except json.JSONDecodeError as e:
            print(f"Failed to decode JSON: {e}")
            return None
    else:
        print("No <script> tag with type 'application/ld+json' found.")
        return None






#region MetadataGUI
class MetadataGUI:
    def __init__(self, master, file_path):
        if not file_path:
            raise ValueError("No file path provided to MetadataGUI.")
        self.master: tk.Tk = master
        self.file_path = file_path
        self.application_path = self.get_app_path()

        self.metadata: Metadata = self.metadata.get_metadata(file_path)
        self.civit: Civit = self.civit.get_civit(file_path)
        self.build_main_window()
        try:
            self.build_main_window(self.civit, self.metadata)
        except Exception as e:
            logger.error(e, exc_info=1)
            self.build_fallback_window(f"Error: {e}\n\nModel Hash: {self.metadata.safetensors_hash}\n\n{self.metadata.pretty_metadata}")



    def get_app_path(self):
        if getattr(sys, 'frozen', False):
            return sys._MEIPASS
        elif __file__:
            return os.path.dirname(__file__)
        return ""


#region Framework
    def build_main_window(self,  model_hash, model_name, initial_text_height=1):
        self.master.title(self.civit_data["modelName"])
        self.master.geometry("1600x1250")  # Set the initial window size
        self.master.resizable(False, True)
        self.master.grid_rowconfigure(0, weight=10,minsize=500)
        self.master.grid_rowconfigure(1, weight=0, minsize=self.initial_text_height)
        self.master.grid_columnconfigure(0, weight=1)

        image_frame = Frame(self.master)
        image_frame.grid(row=0, column=0, sticky='nsew')
        image_frame.grid_rowconfigure(0, weight=1)
        image_frame.grid_columnconfigure(0, weight=1)

        canvas = Canvas(image_frame)
        scrollbar_y = Scrollbar(image_frame, orient="vertical", command=canvas.yview)
        scrollbar_x = Scrollbar(image_frame, orient="horizontal", command=canvas.xview)
        scrollable_frame = Frame(canvas)
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        model_preview_images = self.create_collage(self.civit.image_urls)
        collage_tk = ImageTk.PhotoImage(model_preview_images)
        label = tk.Label(scrollable_frame, image=collage_tk)
        label.pack()
        canvas.grid(row=0, column=0, sticky='nsew')
        scrollbar_y.grid(row=0, column=1, sticky='ns')
        scrollbar_x.grid(row=1, column=0, sticky='ew')
        text_frame = Frame(self.master,height=self.initial_text_height)
        text_frame.grid(row=1, column=0, sticky='nsew')
        text_frame.grid_rowconfigure(0, weight=0,minsize=1)
        text_frame.grid_columnconfigure(0, weight=1)
        text_frame.grid_propagate(False)  # Prevent the frame from resizing to fit the text widget
        scrollbar_text = Scrollbar(text_frame)
        scrollbar_text.pack(side='right', fill='y')
        text_widget = Text(text_frame, wrap='word', yscrollcommand=scrollbar_text.set)
        text_widget.pack(fill='both', expand=True)
        scrollbar_text.config(command=text_widget.yview)

        #"modelId","modelName","trainedWords","imageUrls"
        self.add_hyperlink(text_widget, self.civit.model_id, f"Model Page: {self.civit.model_name}")
        trained_words = ",\n".join(self.civit.trained_words)
        text_widget.insert('2.0', f"\n\nModel Hash: {self.metadata.model_hash}\n\n----\nDescription:\n\n{self.civit.model_name}\n\n----\nTrained Words:\n\n{self.civit.trained_words}\n\n----\nImplicit Data:\n\n{self.metadata.pretty_text}")
        text_widget.config(state='normal')  # Make the text widget editable

        canvas.bind_all("<MouseWheel>", lambda e: self.on_mousewheel(e, canvas))
        canvas.bind_all("<Shift-MouseWheel>", lambda e: self.on_shift_mousewheel(e, canvas))
        self.master.bind('<Escape>', self.close_window)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )


    def build_fallback_window(self, pretty_text):
        default_height = 500
        default_width = 350
        self.master.geometry(f"{default_width}x{default_height}")
        self.master.grid_rowconfigure(0, weight=1)
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_columnconfigure(1, weight=0)
        text_widget = tk.Text(self.master, wrap='word')
        text_widget.insert(tk.END, f"{pretty_text}")
        text_widget.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        scrollbar = tk.Scrollbar(self.master, orient=tk.VERTICAL, command=text_widget.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')

        # Disable editing
        text_widget.config(state=tk.DISABLED)
        text_widget.config(yscrollcommand=scrollbar.set)



    def on_mousewheel(self, event, canvas):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")


    def on_shift_mousewheel(self, event, canvas):
        canvas.xview_scroll(int(-1*(event.delta/120)), "units")


    def open_url(self, url):
        webbrowser.open_new(url)


    def add_hyperlink(self, text_widget, model_id, display_text):
        model_url = MODEL_PAGE_URL_PREFIX + str(model_id)
        def click(event):
            self.open_url(model_url)
            return "break"
        tag_name = f"hyperlink-{model_url}"
        text_widget.insert(tk.END, display_text, tag_name)
        text_widget.tag_config(tag_name, foreground="blue", underline=True)
        text_widget.tag_bind(tag_name, "<Enter>", lambda e: text_widget.config(cursor="hand2"))
        text_widget.tag_bind(tag_name, "<Leave>", lambda e: text_widget.config(cursor=""))
        text_widget.tag_bind(tag_name, "<Button-1>", click)


    def close_window(self, event=None):
        self.master.destroy()


    #region GUI Logic
    def create_collage(self, image_urls, cols=4, max_thumbnail_size=(400, 400)):
        images = self.fetch_images_concurrently(image_urls)
        if not images:
            logger.error("No images to create a collage.")
            return None
        max_width, max_height = max_thumbnail_size
        images = [self.resize_image(img, max_width, max_height) for img in images if img]
        rows = (len(images) // cols) + (len(images) % cols > 0)
        collage_width = cols * max_thumbnail_size[0]
        collage_height = rows * max_thumbnail_size[1]
        collage = Image.new('RGB', (collage_width, collage_height), (255, 255, 255))
        for i, image in enumerate(images):
            x = (i % cols) * max_thumbnail_size[0]
            y = (i // cols) * max_thumbnail_size[1]
            collage.paste(image, (x, y))
        return collage


    def resize_image(self, image, max_width, max_height):
        width_ratio = max_width / image.width
        height_ratio = max_height / image.height
        min_ratio = min(width_ratio, height_ratio)
        new_size = (int(image.width * min_ratio), int(image.height * min_ratio))
        return image.resize(new_size, Image.LANCZOS)





#region Web
class Civit:
    def __init__(self):
        self.session = requests.Session()
        self.data = None #"modelId","description", "modelName","trainedWords","imageUrls"
        self.model_id = None
        self.trained_words = None
        self.model_name = None
        self.description = None
        self.image_urls = None
        self.images = None


    @staticmethod
    def get_civit(safetensors_hash, parseheader=True, quiet=True):
        web_handler: Civit = Civit()
        web_handler._parse(safetensors_hash, quiet, parseheader)
        return web_handler


    def _parse(self, safetensors_hash, quiet=True, parseheader=True):
        self.json = self._fetch_model_json(safetensors_hash)
        self.data = self._extract_model_data(self.json) #"modelId","description", "modelName","trainedWords","imageUrls"
        self.images = self._fetch_images_concurrently(self.image_urls)


    def _fetch_images_concurrently(self, image_urls):
        images = []
        with self.session as session:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [executor.submit(self._fetch_image, session, url) for url in image_urls]
                for i, future in enumerate(concurrent.futures.as_completed(futures)):
                    image_bytes = future.result()
                    if image_bytes:
                        try:
                            image = Image.open(BytesIO(image_bytes))
                            images.append(image)
                            logging.info(f"Successfully fetched image {i+1}/{len(image_urls)}")
                        except Exception as e:
                            logging.error(f"Error processing image {i+1}/{len(image_urls)}: {e}")
                    else:
                        logging.warning(f"Failed to fetch image {i+1}/{len(image_urls)}")
        return images


    def _fetch_image(self, url):
        try:
            response = self.session.get(url)
            response.raise_for_status()  # Raise an HTTPError for bad responses
            return response.content
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching {url}: {e}")
            return None


    def _fetch_model_json(self, safetensors_hash):
        url = API_URL_PREFIX + str(safetensors_hash)
        try:
            # Fetch the image from the URL
            response = self.session.get(url)
            response.raise_for_status()  # Check if the request was successful
            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text(separator='\n', strip=True)
            return text
        except Exception as e:
            logger.error(f"Failed to load json from {url}: {e}")


    def _extract_model_data(self, json_data):
        def clean_json(json_str):
            json_str = re.sub(r'[\x00-\x1F\x7F]', '', json_str)
            return json_str
        if isinstance(json_data, str):
            json_data = json.loads(clean_json(json_data))
        extracted_data = {
            "modelId": None,
            "modelName": "",
            "trainedWords": [],
            "description": "",
            "imageUrls": []
        }
        if 'modelId' in json_data:
            extracted_data["modelId"] = json_data["modelId"]
        if 'description' in json_data:
            extracted_data["description"] = json_data["description"]
        if 'model' in json_data:
            model_name = json_data["model"]["name"]
            if 'name' in json_data:
                model_name += f" - {json_data['name']}"
            extracted_data["modelName"] = model_name
        if 'trainedWords' in json_data:
            extracted_data["trainedWords"] = json_data["trainedWords"]
        if 'images' in json_data and isinstance(json_data['images'], list):
            for image in json_data['images']:
                if 'url' in image:
                    extracted_data["imageUrls"].append(image['url'])
        self.model_id = str(extracted_data["modelId"])
        self.model_name = str(extracted_data["modelName"])
        self.trained_words = str(extracted_data["trainedWords"])
        self.description = str(extracted_data["description"])
        self.image_urls = extracted_data["imageUrls"]
        return extracted_data


#region Safetensors
class Safetensors:
    def __init__(self):
        self.file_handle = None         #file handle
        self.header_byte_buffer = None    #header byte buffer
        self.header = None    #parsed header as a dict
        self.sha_hash = 0

    def __del__(self):
        self.close_file()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close_file()


    @staticmethod
    def get_file(filename:str, quiet=False, parseHeader=True):
        safetensor: Safetensors = Safetensors()
        safetensor._open(filename, quiet, parseHeader)
        return safetensor


    def _open(self, file_name:str, quiet=False, parseHeader=True) -> int:
        file_stats = os.stat(file_name)
        if file_stats.st_size < 8:
            raise SafetensorsException.invalid_file(file_name, "Length less than 8 bytes")
        with open(file_name, "rb") as file_handle:
            self.sha_hash = retrieve_sha256_hash(file_name)
        with open(file_name, "rb") as file_handle:
            b8 = file_handle.read(8)  # read header size
            if len(b8) != 8:
                raise SafetensorsException.invalid_file(file_name, f"Read only {len(b8)} bytes at start of file")
            header_length = int.from_bytes(b8, 'little', signed=False)
            if 8 + header_length > file_stats.st_size:
                raise SafetensorsException.invalid_file(file_name, "Header extends past end of file")
            header_byte_buffer = file_handle.read(header_length)
            if len(header_byte_buffer) != header_length:
                raise SafetensorsException.invalid_file(file_name, f"header size is {header_length}, but read {len(header_byte_buffer)} bytes")
            self.filename = file_name
            self.file_stats = file_stats
            self.file_handle = file_handle
            self.header_byte_buffer = header_byte_buffer.decode("utf-8")
            self.header_length = header_length
            if not quiet:
                logger.info(f"{self.filename}: length={self.file_stats.st_size}, header length={self.header_length}, byte buffer={self.header_byte_buffer}")
            if parseHeader:
                self._CheckDuplicateHeaderKeys()
                self.header = json.loads(self.header_byte_buffer)
        return None


    def get_header(self):
        return self.header


    def get_hash(self):
        return self.sha_hash


    def close_file(self):
        if self.file_handle is not None:
            self.file_handle.close()
            self.file_handle=None
            self.filename=""


    def _CheckDuplicateHeaderKeys(self):
        def parse_object_pairs(pairs):
            return [k for k,_ in pairs]
        keys = json.loads(self.header_byte_buffer, object_pairs_hook=parse_object_pairs)
        header_duplicate_check = {}
        for k in keys:
            if k in header_duplicate_check:
                header_duplicate_check[k] = header_duplicate_check[k]+1
            else:
                header_duplicate_check[k] = 1
        hasError = False
        for k,v in header_duplicate_check.items():
            if v > 1:
                logger.error(f"key {k} used {v} times in header",file=sys.stderr)
                hasError = True
        if hasError:
            raise SafetensorsException.invalid_file(self.filename, "Duplicate keys in header")



#region Metadata
class Metadata:
    """
    A class to store and manage metadata information for a Safetensors file.

    Attributes:
    ----------
    file_path : str
        Path to the Safetensors file.
    safetensors_file : Safetensors
        An instance of the `Safetensors` class representing the cached data of the Safetensors file.
    safetensors_hash : str
        A hash of the Safetensors file, used to retrieve model information from Civit.
    header : dict
        The parsed header information from the Safetensors file.
    metadata_dict : str
        A dictionary of metadata from the Safetensors header.
    metadata_report : str
        The text payload to be displayed in the GUI.
    rec_tags : str
        Top 10 recommended tags.
    stripped_tags : str
        A string representation of (tag, frequency) pairs for easier display or processing.
    pretty_metadata : str
        A formatted version of the metadata json for easier human readability.
    """

    def __init__(self):
        self.file_path: str = None
        self.safetensors_file: Safetensors = None
        self.safetensors_hash: str = None
        self.header = None
        self.metadata_dict: str = None
        self.metadata_report: str = None
        self.rec_tags: str = None
        self.stripped_tags: str = None
        self.pretty_metadata: str = None


    @staticmethod
    def get_metadata(file_path):
        metadata_handler: Metadata = Metadata()
        metadata_handler._process_metadata(file_path)
        return metadata_handler


    def _process_metadata(self, file_path):
        self.file_path= file_path
        self.safetensors_file = self._get_safetensors_file(self.file_path)
        self.safetensors_hash = self.safetensors_file.get_hash()
        self.header = self.safetensors_file.get_header()
        self.metadata_report = self._get_implicit_metadata_report(self.header)


    def _get_safetensors_file(self, file_path, quiet=True):
        safetensors_file = Safetensors.get_file(file_path, quiet) # omits the first non-JSON line
        return safetensors_file


    def _get_implicit_metadata_report(self, header: dict, tag_count=10):
        metadata = header.get("__metadata__", {})
        AliRecursiveJSONLoader(metadata)
        pretty_metadata = json.dumps(metadata, ensure_ascii=False, separators=(', ', ': '), indent=2)
        ss_tag_frequency: str|bytes|bytearray = metadata.get("ss_tag_frequency", {})
        ss_tag_frequency_dict: dict = next(iter(ss_tag_frequency.values()), {})
        filtered_tags = self._get_filtered_tags(ss_tag_frequency_dict)
        metadata_report = ""
        if filtered_tags:
            pretty_tags = json.dumps(filtered_tags, ensure_ascii=False, separators=(', ', ': '), indent=0)
            stripped_tags = pretty_tags.strip("{} \n")
            rec_tags = self._get_top_tags(filtered_tags, tag_count)
            metadata_report = f"{stripped_tags}\n\nTop {tag_count} tags:\n{rec_tags}\n\nMetadata:\n{pretty_metadata}"
            self.rec_tags = rec_tags
            self.stripped_tags = stripped_tags
        else:
            metadata_report = f"No implicit tag information\n\nMetadata:\n{pretty_metadata}"
        #logger.debug(f"::::{pretty_metadata}")
        self.metadata_dict = metadata
        self.pretty_metadata = pretty_metadata
        self.metadata_report = metadata_report


    def _get_top_tags(self, dictionary:dict, amount:int):
        if amount <= 0:
                return ""
        keys = list(dictionary.keys())[:amount]
        return ",".join(keys)


    def _get_filtered_tags(self, ss_tag_frequency_dict: dict):
        def filter_above_percentile(percentile: float) -> dict:
            values = list(ss_tag_frequency_dict.values())
            # Compute the percentile threshold
            threshold = np.percentile(values, percentile)
            filtered_data = {k: v for k, v in filtered_ss_tag_frequency_dict.items() if v >= threshold}
            return filtered_data

        def sort_dict_by_values(data: dict) -> dict:
            sorted_items = sorted(data.items(), key=lambda item: item[1],reverse=True)
            sorted_dict = {k: v for k, v in sorted_items}
            return sorted_dict

        if ss_tag_frequency_dict:
            tag_count = len(ss_tag_frequency_dict.items())
            match tag_count:
                case tag_count if tag_count > 500:
                    filtered_ss_tag_frequency_dict = filter_above_percentile(ss_tag_frequency_dict,99)
                case tag_count if tag_count > 250:
                    filtered_ss_tag_frequency_dict = filter_above_percentile(ss_tag_frequency_dict,97)
                case tag_count if tag_count > 100:
                    filtered_ss_tag_frequency_dict = filter_above_percentile(ss_tag_frequency_dict,95)
                case tag_count if tag_count > 50:
                    filtered_ss_tag_frequency_dict = filter_above_percentile(ss_tag_frequency_dict,90)
                case tag_count if tag_count > 20:
                    filtered_ss_tag_frequency_dict = filter_above_percentile(ss_tag_frequency_dict,50)
                case _:
                    filtered_ss_tag_frequency_dict = ss_tag_frequency_dict
            sorted_filtered_ss_tag_frequency_dict = sort_dict_by_values(filtered_ss_tag_frequency_dict)
            AliRecursiveJSONLoader(sorted_filtered_ss_tag_frequency_dict)
            return sorted_filtered_ss_tag_frequency_dict
        return None


#region Helpers
def retrieve_sha256_hash(file_path, ads_stream_name="sha256", create_alternate_data_stream=True, create_hash_file=False, force_compute=False):
    def compute_hash(file_path, create_alternate_data_stream, create_hash_file):
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for byte_block in iter(lambda: f.read(8192), b""):
                    sha256_hash.update(byte_block)
            hash = sha256_hash.hexdigest()
            if create_hash_file:
                write_hash_file(file_path, hash)
            if create_alternate_data_stream:
                write_hash_ADS(file_path, hash)
            return hash
        except Exception as e:
            logger.error(f"Hash could not be computed: {e}")
            return None

    def write_hash_ADS(file_path, stream_value, stream_name=ads_stream_name,):
        ads_path = f"{file_path}:{stream_name}"
        try:
            with open(ads_path, 'w') as ads:
                ads.write(stream_value)
        except Exception as e:
            logger.error(f"Error setting alternate data stream on file {ads_path}: {e}")

    def read_hash_ADS(file_path, stream_name):
        ads_path = f"{file_path}:{stream_name}"
        try:
            with open(ads_path, 'r') as ads:
                content = ads.read()
                return content
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Error reading ADS {ads_path}: {e}")
            return None

    def read_hash_file(file_path):
        file_no_ext = os.path.splitext(file_path)[0]
        hash_file_path = file_no_ext + ".sha256"
        if os.path.isfile(hash_file_path):
            try:
                with open(hash_file_path, "r") as f:
                    content = f.read().strip()
                logger.info(f"Hash retrieved from hash file {hash_file_path}: {content}")
                return content
            except OSError as e:
                logger.error(f"Error reading existing hash file {hash_file_path}: {e}")

    def write_hash_file(file_path, hash_value):
        file_no_ext = os.path.splitext(file_path)[0]
        hash_file_path = file_no_ext + ".sha256"
        try:
            with open(hash_file_path, "w") as f:
                f.write(hash_value)
                logger.info(f"Hash computed and set to hash file {hash_file_path}: {hash_value}")
        except OSError as e:
            logger.error(f"Error writing to hash file: {e}")

    if force_compute:
        model_hash = compute_hash(file_path, create_alternate_data_stream, create_hash_file)
    else:
        model_hash = read_hash_ADS(file_path, ads_stream_name)
        if not model_hash:
            model_hash = read_hash_file(file_path)
            if not model_hash:
                model_hash = compute_hash(file_path, create_alternate_data_stream, create_hash_file)
    return model_hash


def AliRecursiveJSONLoader(data: dict) -> None:
    """
    Recursively parse and pretty print nested JSON dict in place.

    This function attempts to convert serialized JSON strings within the dictionary
    into nested dictionaries and lists for better readability.

    Example:
        Input:
            {
                "ss_dataset_dirs": "{\"abc\": {\"n_repeats\": 2, \"img_count\": 60}}",
                "nested_list": "[\"{\\\"key1\\\": \\\"value1\\\"}\", \"{\\\"key2\\\": \\\"value2\\\"}\"]",
                "more_nested": "{\"level1\": \"{\\\"level2\\\": {\\\"level3\\\": \\\"value\\\"}}\"}"
            }
        Output:
            {
                "ss_dataset_dirs": {
                    "abc": {
                        "n_repeats": 2,
                        "img_count": 60
                    }
                },
                "nested_list": [
                    {
                        "key1": "value1"
                    },
                    {
                        "key2": "value2"
                    }
                ],
                "more_nested": {
                    "level1": {
                        "level2": {
                            "level3": "value"
                        }
                    }
                }
            }
    """
    for key, value in data.items():
        if isinstance(value, str):
            try:
                data[key] = json.loads(value)
            except json.JSONDecodeError:
                continue
        if isinstance(data[key], dict):
            AliRecursiveJSONLoader(data[key])
        elif isinstance(data[key], list):
            for i, item in enumerate(data[key]):
                if isinstance(item, str):
                    try:
                        data[key][i] = json.loads(item)
                    except json.JSONDecodeError:
                        continue
                elif isinstance(item, dict):
                    AliRecursiveJSONLoader(item)


def main(file_path=""):
    root = tk.Tk()
    app = MetadataGUI(root, file_path)
    root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        main(file_path)
    else:
        main(TEST_FILE_PATH)


