import os
import logging

log_file_path = os.path.splitext(os.path.abspath(__file__))[0] + ".log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(log_file_path)
    ]
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






#region Framework

def get_app_path():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    elif __file__:
        return os.path.dirname(__file__)
    return ""



#region GUI Logic
def display_collage_in_tkinter(model_data,implicit_data,model_hash, model_description, initial_text_height=1):
    def on_mousewheel(event, canvas):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def on_shift_mousewheel(event, canvas):
        canvas.xview_scroll(int(-1*(event.delta/120)), "units")

    def open_url(url):
        webbrowser.open_new(url)

    def add_hyperlink(text_widget, model_id, display_text):
        model_url = MODEL_PAGE_URL_PREFIX + str(model_id)
        def click(event):
            open_url(model_url)
            return "break"

        tag_name = f"hyperlink-{model_url}"
        text_widget.insert(tk.END, display_text, tag_name)
        text_widget.tag_config(tag_name, foreground="blue", underline=True)
        text_widget.tag_bind(tag_name, "<Enter>", lambda e: text_widget.config(cursor="hand2"))
        text_widget.tag_bind(tag_name, "<Leave>", lambda e: text_widget.config(cursor=""))
        text_widget.tag_bind(tag_name, "<Button-1>", click)

    root = tk.Tk()
    root.title(model_data["modelName"])

    def close_window(event=None):
        root.destroy()

    root.bind('<Escape>', close_window)

    root.geometry("1600x1250")  # Set the initial window size
    root.resizable(False, True)
    root.grid_rowconfigure(0, weight=10,minsize=500)
    root.grid_rowconfigure(1, weight=0, minsize=initial_text_height)
    root.grid_columnconfigure(0, weight=1)


    image_frame = Frame(root)
    image_frame.grid(row=0, column=0, sticky='nsew')
    image_frame.grid_rowconfigure(0, weight=1)
    image_frame.grid_columnconfigure(0, weight=1)

    canvas = Canvas(image_frame)
    scrollbar_y = Scrollbar(image_frame, orient="vertical", command=canvas.yview)
    scrollbar_x = Scrollbar(image_frame, orient="horizontal", command=canvas.xview)
    scrollable_frame = Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

    model_preview_images = create_collage(model_data["imageUrls"])
    collage_tk = ImageTk.PhotoImage(model_preview_images)
    label = tk.Label(scrollable_frame, image=collage_tk)
    label.pack()

    canvas.grid(row=0, column=0, sticky='nsew')
    scrollbar_y.grid(row=0, column=1, sticky='ns')
    scrollbar_x.grid(row=1, column=0, sticky='ew')

    canvas.bind_all("<MouseWheel>", lambda e: on_mousewheel(e, canvas))
    canvas.bind_all("<Shift-MouseWheel>", lambda e: on_shift_mousewheel(e, canvas))

    text_frame = Frame(root,height=initial_text_height)
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
    add_hyperlink(text_widget, model_data["modelId"], f"Model Page: {model_data['modelName']}")
    trained_words = ",\n".join(model_data['trainedWords'])
    text_widget.insert('2.0', f"\n\nModel Hash: {model_hash}\n\n----\nDescription:\n\n{model_description}\n\n----\nTrained Words:\n\n{trained_words}\n\n----\nImplicit Data:\n\n{implicit_data}")
    text_widget.config(state='normal')  # Make the text widget editable

    root.mainloop()


def create_collage(image_urls, cols=4, max_thumbnail_size=(400, 400)):
    images = fetch_images_concurrently(image_urls)
    if not images:
        logger.error("No images to create a collage.")
        return None

    max_width, max_height = max_thumbnail_size
    images = [resize_image(img, max_width, max_height) for img in images if img]
    rows = (len(images) // cols) + (len(images) % cols > 0)
    collage_width = cols * max_thumbnail_size[0]
    collage_height = rows * max_thumbnail_size[1]

    collage = Image.new('RGB', (collage_width, collage_height), (255, 255, 255))

    for i, image in enumerate(images):
        x = (i % cols) * max_thumbnail_size[0]
        y = (i // cols) * max_thumbnail_size[1]
        collage.paste(image, (x, y))

    return collage


def display_implicit_data_in_tkinter(pretty_text):
    root = tk.Tk()

    default_height = 500
    default_width = 350
    root.geometry(f"{default_width}x{default_height}")
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=0)

    text_widget = tk.Text(root, wrap='word')



    text_widget.insert(tk.END, f"{pretty_text}")

    text_widget.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
    scrollbar = tk.Scrollbar(root, orient=tk.VERTICAL, command=text_widget.yview)
    scrollbar.grid(row=0, column=1, sticky='ns')

    # Disable editing
    text_widget.config(state=tk.DISABLED)
    text_widget.config(yscrollcommand=scrollbar.set)

    root.mainloop()


#region Local Metadata
def get_implicit_metadata(file_path: str):
    safetensor: SafeTensorsFile = SafeTensorsFile.open_file(file_path, quiet=True) # omits the first non-JSON line
    hash = safetensor.get_hash()
    header: dict = safetensor.get_header()
    metadata = header.get("__metadata__", {})
    AliRecursiveJSONLoader(metadata)
    pretty_metadata = json.dumps(metadata, ensure_ascii=False, separators=(', ', ': '), indent=2)
    #logger.debug(f"::::{pretty_metadata}")
    pretty_text = ""
    ss_tag_frequency: str|bytes|bytearray = metadata.get("ss_tag_frequency", {})
    ss_tag_frequency_dict: dict = next(iter(ss_tag_frequency.values()), {})

    if ss_tag_frequency_dict:
        tag_count = len(ss_tag_frequency_dict.items())
        if tag_count > 500:
            filtered_ss_tag_frequency_dict = filter_above_percentile(ss_tag_frequency_dict,99)
        elif tag_count > 250:
            filtered_ss_tag_frequency_dict = filter_above_percentile(ss_tag_frequency_dict,97)
        elif tag_count > 100:
            filtered_ss_tag_frequency_dict = filter_above_percentile(ss_tag_frequency_dict,95)
        elif tag_count > 50:
            filtered_ss_tag_frequency_dict = filter_above_percentile(ss_tag_frequency_dict,90)
        elif tag_count > 20:
            filtered_ss_tag_frequency_dict = filter_above_percentile(ss_tag_frequency_dict,50)
        else:
            filtered_ss_tag_frequency_dict = ss_tag_frequency_dict

        sorted_filtered_ss_tag_frequency_dict = sort_dict_by_values(filtered_ss_tag_frequency_dict)
        rec_tags = get_recommended_tags(sorted_filtered_ss_tag_frequency_dict,10)
        #pyperclip.copy(rec_tags)

        AliRecursiveJSONLoader(sorted_filtered_ss_tag_frequency_dict)
        pretty_tags = json.dumps(sorted_filtered_ss_tag_frequency_dict, ensure_ascii=False, separators=(', ', ': '), indent=0)
        stripped_tags = pretty_tags.strip("{} \n")
        pretty_text = f"{stripped_tags}\n\nTop 10 tags:\n{rec_tags}\n\nAdditional Implicit Data:\n{pretty_metadata}"
    else:
        pretty_text = f"No implicit tag information"

    return hash,pretty_text


class SafeTensorsException(Exception):
    def __init__(self, msg:str):
        self.msg = msg
        super().__init__(msg)

    @staticmethod
    def invalid_file(filename:str, whatiswrong:str):
        message = f"{filename} is not a valid .safetensors file: {whatiswrong}"
        return SafeTensorsException(msg=message)

    def __str__(self):
        return self.msg


class SafeTensorsFile:
    def __init__(self):
        self.file_handle = None         #file handle
        self.header_byte_buffer = None    #header byte buffer
        self.header = None    #parsed header as a dict
        self.error = 0
        self.sha_hash = 0

    def __del__(self):
        self.close_file()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close_file()


    def close_file(self):
        if self.file_handle is not None:
            self.file_handle.close()
            self.file_handle=None
            self.filename=""


    def _CheckDuplicateHeaderKeys(self):
        def parse_object_pairs(pairs):
            return [k for k,_ in pairs]

        keys=json.loads(self.header_byte_buffer,object_pairs_hook=parse_object_pairs)
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
            raise SafeTensorsException.invalid_file(self.filename,"Duplicate keys in header")


    @staticmethod
    def open_file(filename:str, quiet=False, parseHeader=True):
        safetensor = SafeTensorsFile()
        safetensor.open(filename, quiet, parseHeader)
        return safetensor


    def open(self, file_name:str, quiet=False, parseHeader=True) -> int:
        file_stats = os.stat(file_name)
        if file_stats.st_size < 8:
            raise SafeTensorsException.invalid_file(file_name, "Length less than 8 bytes")

        with open(file_name, "rb") as file_handle:
            self.sha_hash = retrieve_sha256_hash(file_name)

        with open(file_name, "rb") as file_handle:
            b8 = file_handle.read(8)  # read header size
            if len(b8) != 8:
                raise SafeTensorsException.invalid_file(file_name, f"Read only {len(b8)} bytes at start of file")
            header_length = int.from_bytes(b8, 'little', signed=False)

            if 8 + header_length > file_stats.st_size:
                raise SafeTensorsException.invalid_file(file_name, "Header extends past end of file")

            if not quiet:
                logger.info(f"{file_name}: length={file_stats.st_size}, header length={header_length}")

            header_byte_buffer = file_handle.read(header_length)
            if len(header_byte_buffer) != header_length:
                raise SafeTensorsException.invalid_file(file_name, f"header size is {header_length}, but read {len(header_byte_buffer)} bytes")

            self.filename = file_name
            self.file_stats = file_stats
            self.file_handle = file_handle
            self.header_byte_buffer = header_byte_buffer
            self.error = 0
            self.header_length = header_length
            if parseHeader:
                self._CheckDuplicateHeaderKeys()
                self.header = json.loads(self.header_byte_buffer)

        return 0

    def get_header(self):
        return self.header

    def get_hash(self):
        return self.sha_hash


def get_recommended_tags(dictionary:dict,amount:int):
    if amount <= 0:
            return ""
    keys = list(dictionary.keys())[:amount]
    return ",".join(keys)


def filter_above_percentile(data: dict, percentile: float) -> dict:
    # Extract values
    values = list(data.values())
    # Compute the percentile threshold
    threshold = np.percentile(values, percentile)
    # Filter dictionary based on the threshold
    filtered_data = {k: v for k, v in data.items() if v >= threshold}
    return filtered_data


#region Helpers
def sort_dict_by_values(data: dict) -> dict:
    sorted_items = sorted(data.items(), key=lambda item: item[1],reverse=True)
    sorted_dict = {k: v for k, v in sorted_items}
    return sorted_dict


def resize_image(image, max_width, max_height):
    width_ratio = max_width / image.width
    height_ratio = max_height / image.height
    min_ratio = min(width_ratio, height_ratio)
    new_size = (int(image.width * min_ratio), int(image.height * min_ratio))
    return image.resize(new_size, Image.LANCZOS)


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
    import json
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



#region Web
def fetch_image(session, url):
    try:
        response = session.get(url)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        return response.content
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching {url}: {e}")
        return None


def fetch_images_concurrently(image_urls):
    images = []
    with requests.Session() as session:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(fetch_image, session, url) for url in image_urls]
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


#Explicit Data Functions
def fetch_model_json(model_hash):
    url = API_URL_PREFIX + str(model_hash)
    try:
        # Fetch the image from the URL
        response = requests.get(url)
        response.raise_for_status()  # Check if the request was successful
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text(separator='\n', strip=True)
        return text
    except Exception as e:
        logger.error(f"Failed to load json from {url}: {e}")

def extract_model_data(json_data):
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

    return extracted_data





def context_menu_execute(file_path=r"s:\SD_Archive\models\Lora\PONY\_Scoring\_Concept\Pony_XL_AllTheWayThrough_Concept.safetensors"):
    model_hash,implicit_data = get_implicit_metadata(file_path)
    try:
        model_json = fetch_model_json(model_hash)
        model_data = extract_model_data(model_json) #"modelId","description", "modelName","trainedWords","imageUrls"
        model_description = f'{model_data["description"]}'#\n\n{extract_model_text(model_data["modelId"])}'
        display_collage_in_tkinter(model_data, implicit_data,model_hash, model_description)
    except Exception as e:
        logger.error(e,exc_info=1)
        display_implicit_data_in_tkinter(f"Error: {e}\n\nModel Hash: {model_hash}\n\n{implicit_data}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        context_menu_execute(file_path)
    else:
        context_menu_execute()

# root = Tk()
# app = ImgTxtViewer(root)
# root.mainloop()
