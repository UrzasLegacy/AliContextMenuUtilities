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
import time
import sys
import json
import requests
import re
import hashlib
import concurrent.futures
import webbrowser
import numpy as np

import tkinter as tk
from html2text import HTML2Text
from tkinter import Text, Scrollbar, Canvas, Frame
from bs4 import BeautifulSoup
from PIL import Image,ImageTk
from io import BytesIO
from readability import Document
from queue import Queue

API_URL_PREFIX = "https://civitai.com/api/v1/model-versions/by-hash/"
MODEL_PAGE_URL_PREFIX = "https://civitai.com/models/"
MODEL_PAGE_VERSION_PREFIX = "?modelVersionId="
TEST_FILE_PATH = r"s:\SD_Archive\models\Lora\PONY\Style_Top\Pony_XL_Aaaa_2_Style.safetensors"

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
        self.metadata: Metadata = Metadata.get_metadata(file_path)
        self.civit: Civit = Civit.get_civit(self.metadata.safetensors_hash)
        try:
            self.build_main_window()
        except Exception as e:
            logger.error(e, exc_info=1)
            self.build_fallback_window(f"Error: {e}\n\nModel Hash: {self.metadata.safetensors_hash}\n\n{self.metadata.pretty_metadata}")
        self.master.protocol("WM_DELETE_WINDOW", self.close_window)


    def get_app_path(self):
        if getattr(sys, 'frozen', False):
            return sys._MEIPASS
        elif __file__:
            return os.path.dirname(__file__)
        return ""


#region Framework
    def build_main_window(self, initial_text_height=1):
        self.master.title(self.civit.model_name)
        self.master.geometry("1600x1250")  # Set the initial window size
        self.master.resizable(False, True)
        self.master.grid_rowconfigure(0, weight=10,minsize=500)
        self.master.grid_rowconfigure(1, weight=0, minsize=initial_text_height)
        self.master.grid_columnconfigure(0, weight=1)
        self.master.bind('<Escape>', self.close_window)
        self.master.bind('<Control-w>', self.close_window)

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
        model_preview_images = self.create_collage(self.civit.images)
        self.collage_tk = ImageTk.PhotoImage(model_preview_images)
        label = tk.Label(scrollable_frame, image=self.collage_tk)
        label.pack()
        label.bind("<MouseWheel>", lambda e: self.on_mousewheel(e, canvas))
        label.bind("<Shift-MouseWheel>", lambda e: self.on_shift_mousewheel(e, canvas))
        canvas.grid(row=0, column=0, sticky='nsew')
        canvas.bind("<MouseWheel>", lambda e: self.on_mousewheel(e, canvas))
        canvas.bind("<Shift-MouseWheel>", lambda e: self.on_shift_mousewheel(e, canvas))

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        scrollbar_y.grid(row=0, column=1, sticky='ns')
        scrollbar_x.grid(row=1, column=0, sticky='ew')
        text_frame = Frame(self.master,height=initial_text_height)
        text_frame.grid(row=1, column=0, sticky='nsew')
        text_frame.grid_rowconfigure(0, weight=0,minsize=1)
        text_frame.grid_columnconfigure(0, weight=1)
        text_frame.grid_propagate(False)  # Prevent the frame from resizing to fit the text widget


        text_widget = Text(text_frame, wrap='word')
        scrollbar_text = Scrollbar(text_frame)
        scrollbar_text.pack(side='right', fill='y')
        text_widget.pack(fill='both', expand=True)
        text_widget.configure(yscrollcommand=scrollbar_text.set)
        scrollbar_text.config(command=text_widget.yview)

        #"versionId", "modelId","modelName","trainedWords","imageUrls"
        self.add_hyperlink(text_widget, self.civit.version_id, self.civit.model_id, f"Model Page: {self.civit.model_name}\n\n")
        self.add_text_block(text_widget, "Model Hash", self.metadata.safetensors_hash)
        self.add_text_block(text_widget, "Trained Words", self.civit.trained_words)
        self.add_text_block(text_widget, "Top 10 Tags", self.metadata.rec_tags)
        self.add_text_block(text_widget, "Version Description", self.civit.version_description)
        self.add_text_block(text_widget, "Model Description", self.civit.html_text)
        self.add_text_block(text_widget, "File Metadata", self.metadata.metadata_report)

        text_widget.config(state='normal')  # Make the text widget editable


    def build_fallback_window(self, pretty_text):
        self.master.title(self.file_path)
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



    def on_mousewheel(self, event, widget):
        widget.yview_scroll(int(-1*(event.delta/120)), "units")

    def on_shift_mousewheel(self, event, widget):
        widget.xview_scroll(int(-1*(event.delta/120)), "units")


    def open_url(self, url):
        webbrowser.open_new(url)


    def add_text_block(self, text_widget:tk.Text, display_title, display_text):
        text_title = f"{display_title}:"
        text_body = f"\n{display_text}\n\n"
        title_tag = "border_text"
        text_widget.insert(tk.END, text_title, title_tag)
        text_widget.tag_config(title_tag, border=10, borderwidth=1, relief="solid")
        tag_name = f"text_block"
        text_widget.insert(tk.END, text_body, tag_name)
        text_widget.tag_config(tag_name, lmargin1=20, lmargin2=20)


    def add_hyperlink(self, text_widget:tk.Text, version_id, model_id, display_text):
        model_url = MODEL_PAGE_URL_PREFIX + str(model_id) + MODEL_PAGE_VERSION_PREFIX + version_id
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
        self.civit and self.civit.close_sessions()
        self.master.destroy()


    #region GUI Logic
    def create_collage(self, images, cols=4, thumbnail_size=(400,400)):
        if not images:
            logging.error("No images to create a collage.")
            return None
        rows = (len(images) + cols - 1) // cols  # Ceiling division
        thumb_width, thumb_height = thumbnail_size
        collage_width = cols * thumb_width
        collage_height = rows * thumb_height
        collage = Image.new('RGB', (collage_width, collage_height), (255, 255, 255))
        for index, image in enumerate(images):
            row = index // cols
            col = index % cols
            x = col * thumb_width
            y = row * thumb_height
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
    NUM_SESSIONS = 2
    def __init__(self):
        self.data = None #"versionID", "modelId","description", "modelName","trainedWords","imageUrls"
        self.model_id = None
        self.api_json = None
        self.html_text = None
        self.trained_words = None
        self.model_name = None
        self.version_description = None
        self.image_urls = None
        self.images = None
        self.session_pool = Queue()
        self.sessions = []
        for _ in range(self.NUM_SESSIONS):  # Adjust the number of sessions
            session = requests.Session()
            self.session_pool.put(session)
            self.sessions.append(session)


    @staticmethod
    def get_civit(safetensors_hash):
        web_handler: Civit = Civit()
        web_handler._parse(safetensors_hash)
        return web_handler


    def _parse(self, safetensors_hash):
        self.api_json = self._fetch_model_api_json(safetensors_hash)
        self.data = self._extract_model_data(self.api_json) #"versionID", "modelId","version_description", "modelName","trainedWords","imageUrls"

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_html = executor.submit(self._fetch_model_page_html)
            future_images = executor.submit(self._fetch_images_concurrently, self.image_urls, executor)
            self.html_text = future_html.result()
            self.images = future_images.result()


    def html_to_markdown(self, html_text):
        html_converter = HTML2Text()
        html_converter.ignore_links = False  # Keep links in the output
        markdown_text = html_converter.handle(html_text)
        return markdown_text.strip()


    def _fetch_images_concurrently(self, image_urls, executor):
        images = []
        futures = [executor.submit(self._fetch_image, url) for url in image_urls]
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            image = future.result()
            if image:
                images.append(image)
                #logging.info(f"Successfully fetched image {i+1}/{len(image_urls)}")
            else:
                logging.warning(f"Failed to fetch image {i+1}/{len(image_urls)}")
        return images


    def _fetch_image(self, url, thumbnail_size=(400,400)):
        session = self.session_pool.get()
        try:
            response = session.get(url)
            response.raise_for_status()  # Raise an HTTPError for bad responses
            image = Image.open(BytesIO(response.content))
            image.thumbnail(thumbnail_size, Image.BICUBIC)
            return image

        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching {url}: {e}")
            return None
        finally:
            self.session_pool.put(session)


    def _fetch_model_api_json(self, safetensors_hash):
        url = API_URL_PREFIX + str(safetensors_hash)
        session = self.session_pool.get()
        try:
            response = session.get(url)
            response.raise_for_status()  # Check if the request was successful
            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text(separator='\n', strip=True)
            return text
        except Exception as e:
            logger.error(f"Failed to load api_json from {url}: {e}")
        finally:
            self.session_pool.put(session)


    def _fetch_model_page_html(self):
        model_url = MODEL_PAGE_URL_PREFIX + self.model_id + MODEL_PAGE_VERSION_PREFIX + self.version_id
        session = self.session_pool.get()
        try:
            response = session.get(model_url)
            response.raise_for_status()  # Check if the request was successful
            html_doc = Document(response.text)
            return self.html_to_markdown(html_doc.summary())
        except Exception as e:
            logger.error(f"Failed to load html from {model_url}: {e}")
        finally:
            self.session_pool.put(session)


    def close_sessions(self):
        for session in self.sessions:
            session.close()


    def _extract_model_data(self, json_data):
        def clean_json(json_str):
            json_str = re.sub(r'[\x00-\x1F\x7F]', '', json_str)
            return json_str

        if isinstance(json_data, str):
            json_data = json.loads(clean_json(json_data))
        # AliRecursiveJSONLoader(json_data)
        # logger.debug(json.dumps(json_data, indent=2))
        extracted_data = {
            "modelId": None,
            "versionId": None,
            "modelName": "",
            "trainedWords": [],
            "version_description": "",
            "imageUrls": []
        }
        if 'id' in json_data:
            extracted_data["versionId"] = json_data["id"]
        if 'modelId' in json_data:
            extracted_data["modelId"] = json_data["modelId"]
        if 'description' in json_data:
            extracted_data["version_description"] = json_data["description"]
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
        self.version_id = str(extracted_data["versionId"])
        self.model_id = str(extracted_data["modelId"])
        self.model_name = str(extracted_data["modelName"])
        self.trained_words =",\n".join(extracted_data["trainedWords"])
        self.version_description = str(extracted_data["version_description"])
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
            metadata_report = f"{stripped_tags}\n\nMetadata:\n{pretty_metadata}"
            self.rec_tags = rec_tags
            self.stripped_tags = stripped_tags
        else:
            metadata_report = f"No implicit tag information\n\nMetadata:\n{pretty_metadata}"
        #logger.debug(f"::::{pretty_metadata}")
        self.metadata_dict = metadata
        self.pretty_metadata = pretty_metadata
        return metadata_report

    def _get_top_tags(self, dictionary:dict, amount:int):
        if amount <= 0:
                return ""
        keys = list(dictionary.keys())[:amount]
        return ",".join(keys)


    def _get_filtered_tags(self, ss_tag_frequency_dict: dict):
        def filter_above_percentile(ss_tag_frequency_dict, percentile: float) -> dict:
            values = list(ss_tag_frequency_dict.values())
            # Compute the percentile threshold
            threshold = np.percentile(values, percentile)
            filtered_data = {k: v for k, v in ss_tag_frequency_dict.items() if v >= threshold}
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
    s = time.time()
    app = MetadataGUI(root, file_path)
    print("e:", time.time() - s)
    root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        main(file_path)
    else:
        main(TEST_FILE_PATH)


