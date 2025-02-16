import os
import logging
import sys
import json
import requests
import re
import hashlib
import concurrent.futures
import webbrowser
import numpy as np

from requests.cookies import RequestsCookieJar
import pyperclip
import tkinter as tk
from html2text import HTML2Text
from tkinter import Text, Scrollbar, Canvas, Frame

# from bs4 import BeautifulSoup # Dont need for now, only loading raw JSON data
from PIL import Image, ImageTk
from io import BytesIO
from readability import Document
from queue import Queue

log_file_path = os.path.splitext(os.path.abspath(__file__))[0] + ".log"
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.FileHandler(log_file_path)],
)
logger = logging.getLogger(__name__)


API_URL_HASH_PREFIX = "https://civitai.com/api/v1/model-versions/by-hash/"
API_URL_MODELS_PREFIX = "https://civitai.com/api/v1/models/"
MODEL_PAGE_URL_PREFIX = "https://civitai.com/models/"
MODEL_PAGE_VERSION_PREFIX = "?modelVersionId="
access_cookie = "eyJhbGciOiJkaXIiLCJlbmMiOiJBMjU2R0NNIn0..1QM6py1244wFADJk.yTmzVzjCVU2GbZWLQPH02NUayOZ6_Zefendxp-CHQOaHD8EBpMFajMSDs-WMLsUR81pfOET3CClnHr7tYDa24UUh9MDu8vyfUgg3TF6KATLb3X3RkiHganCeo2Jwh_h-pv334b1KdKr7TR0PLd3VZuMxx6-2NdUZJhhxyQgUEct_c3UnnF91wVVRLtkf2xHXpYMISfeWCaYdKOjaTBNPbKAsDUZSdt6tY435EPHiQyunuGWZSr9Fx2hsJBsn6uOPnwvmMiUZZekNS7LnMDUEKTOyRuydy8JVVYQTFQSN28mr_r9nfFQlI8kJHgsoFC4_p18M1lk-4ZHbPzTNoJ2AaURp8qbWAdT6dFQBUGkkMIzL_rhDeHDn8mlGid-OXtRGeVsEwOTzU7bUuwclAWCaWXjSbRGzQ5d6kD0lEdJhDSEJmeVcM5S_Rik1y2MFry4p9rEPc8pYI7xIn3fMj_PubWKhvW5K1G_GHaepJ0QBc8_ZDjuB3Jmf_RspyYvDUlJI9TTfKWl3_70wrIJVaa9q8jlpUtkZseoV_GunQ9iYT4xkdbBFCjyp-oCPF3-XqN3j0-vCJkPCpVUsjqf5eP7ETr60i4CmDzUKXPOLabXKXvS7TaA2b4Gi4sN7uBDmOHMYjEqdrl_LlA2HP3hPehdig5tTTToCytOsM-rgKHLff3qVRW5nTkvsHh_mGD5VOqhpYs4XJGvZA1-D7KSAUpZ7nBBpDbF4w8lHbS-Oe-eg_DdMdw0eR7cbHKCppn9wOfUBB72HeQUB1jNriqa3fTT-16uISOEdyT57ASVbdej5IQz_OwHAz4nNSFuO9pc7nmTxrR84mq33ad56otaPX1RuEqiA0xbLRmD9e_AWN7ef_zYbOi8o1OfqK-CxdH_RcxMjCjp6ECJdSn13pmzGZZ7Gzotm6gZFjblWm1oqbXyeMx1cSb03cOYEKQ9C4_Z2SwBJE3BSiRuQDAZMzocugD3Yj7M_v9AUL6EGuu9pM-a1qt6EwUQj4_cxtBKGkJb4cKqm2q8QGcTwZf3_tNB6sJ6VC0PBzf3DlANrP0-Afj4Zb6755W5xiDK9cxTj3xKBmLKC72uQrwRYh-WwkdnjqbvsnOS4QK1TKCGuZwRPYL7viNfzLtpHqxDCPGs-ijS2gWogsA4bNbVudOjGJBgN4xrk_hqDsvdxVGZipuTZqdac0LjYsiSWik1evGReU4vSkQ3_MErMtDyadEQwMjkcpNIjk0I.4Tfi4q1Ntyj46GHtuFs-Dw"
stripe_mid = "04088e78-d4fe-4e7b-a7fd-b1efa069ec3773094b"
cf_clearance = ".e.ifysy0K0gNnEezAzp5LDTrcQISt0yynwaOmcA41U-1715975542-1.0.1.1-19lH5Ec4X53xlZXFHcWj7wRFc6kMVxeZGarMyJwUCRn5Ic5z4hJqqc_y1e04sgNEV6mfMi9PMcsoRhhieeyRKA"
ph_phc_MRWB5oArnYNY437MmczkYEQ6qWydDqsq1NqzpFjg8OI_posthog = "%7B%22distinct_id%22%3A%221679166%22%2C%22%24device_id%22%3A%22018e2f1c-8423-7e1c-bea8-223d1fa5de63%22%2C%22%24user_state%22%3A%22identified%22%2C%22%24user_id%22%3A%221679166%22%2C%22%24stored_person_properties%22%3A%7B%22name%22%3A%22alistormccoy%22%2C%22email%22%3A%22alistormccoy%40gmail.com%22%7D%2C%22%24sesid%22%3A%5B1710187382111%2C%22018e2f1c-8425-7605-90e2-dabbf090e9df%22%2C1710187381797%5D%2C%22%24active_feature_flags%22%3A%5B%5D%2C%22%24enabled_feature_flags%22%3A%7B%7D%2C%22%24feature_flag_payloads%22%3A%7B%7D%2C%22%24session_recording_enabled_server_side%22%3Atrue%2C%22%24console_log_recording_enabled_server_side%22%3Atrue%2C%22%24session_recording_recorder_version_server_side%22%3A%22v2%22%2C%22%24autocapture_disabled_server_side%22%3Atrue%7D"
ref_landing_page = "%2Fimages%2F43490525"
csrf = "c7ffbf1e0bfe16bb9d4aab9eceebb89457ca8f14b5f33493b5b8dbdeda42d330%7Cf0b36623fd1772e16652b52e964c0b77e6a943306c719dc3061ce8cdc2380dcd"
Secure = "https%3A%2F%2Fcivitai.com"
# TODO sort image urls so their display order is consistent
# TODO add file path display
# TODO autoadd model to hash dictionary C:\AliProjects\StableDiffusion\AliComfy\AliNodes\AliHashes.json
# TODO utility function to add an entry: load dictionary, set model hash key to the value of [lora_name, lora_path]


class SafetensorsException(Exception):
    def __init__(self, msg: str):
        self.msg = msg
        super().__init__(msg)

    @staticmethod
    def invalid_file(filename: str, whatiswrong: str):
        message = f"{filename} is not a valid .safetensors file: {whatiswrong}"
        return SafetensorsException(msg=message)

    def __str__(self):
        return self.msg


# region MetadataGUI


class MetadataGUI:
    def __init__(self, master: tk.Tk, file_path):
        if not file_path:
            raise ValueError("No file path provided to MetadataGUI.")
        self.master = master
        self.file_path = file_path
        # self.application_path = self.get_app_path()
        self.metadata: Metadata = Metadata.get_metadata(file_path)
        self.civit: Civit = Civit.get_civit(self.metadata.safetensors_hash)
        try:
            self.build_main_window()
        except Exception as e:
            logger.error(e, exc_info=1)
            self.build_fallback_window(e)
        self.master.protocol("WM_DELETE_WINDOW", self.close_window)
        self.master.attributes("-topmost", True)
        self.master.after(0, self.master.attributes, "-topmost", False)

    def get_app_path(self):
        if getattr(sys, "frozen", False):
            return sys._MEIPASS
        elif __file__:
            return os.path.dirname(__file__)
        return ""

    # region Framework

    def build_main_window(self, initial_text_height=1):
        self.master.title(self.civit.model_name)
        self.master.geometry("1600x1250")  # Set the initial window size
        self.master.resizable(False, True)
        self.master.grid_rowconfigure(0, weight=10, minsize=500)
        self.master.grid_rowconfigure(1, weight=0, minsize=initial_text_height)
        self.master.grid_columnconfigure(0, weight=1)
        self.master.bind("<Escape>", self.close_window)
        self.master.bind("<Control-w>", self.close_window)

        image_frame = Frame(self.master)
        image_frame.grid(row=0, column=0, sticky="nsew")
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
        canvas.grid(row=0, column=0, sticky="nsew")
        canvas.bind("<MouseWheel>", lambda e: self.on_mousewheel(e, canvas))
        canvas.bind("<Shift-MouseWheel>", lambda e: self.on_shift_mousewheel(e, canvas))

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        text_frame = Frame(self.master, height=initial_text_height)
        text_frame.grid(row=1, column=0, sticky="nsew")
        text_frame.grid_rowconfigure(0, weight=0, minsize=1)
        text_frame.grid_columnconfigure(0, weight=1)
        text_frame.grid_propagate(False)  # Prevent the frame from resizing to fit the text widget
        text_widget = Text(text_frame, wrap="word")
        scrollbar_text = Scrollbar(text_frame)
        scrollbar_text.pack(side="right", fill="y")
        text_widget.pack(fill="both", expand=True)
        text_widget.configure(yscrollcommand=scrollbar_text.set)
        scrollbar_text.config(command=text_widget.yview)

        button_frame = tk.Frame(self.master, height=25)
        button_frame.grid(row=2, column=0, sticky="nsew")

        self.add_hyperlink(
            text_widget, self.civit.version_id, self.civit.model_id, f"Model Page: {self.civit.model_name}\n\n"
        )
        self.add_text_block(text_widget, "Creator", self.civit.creator_name)
        self.add_text_block(text_widget, "Base Model", self.civit.base_model_name)
        self.add_text_block(text_widget, "Model Hash", self.metadata.safetensors_hash)
        self.add_ez_copy(text_widget)
        self.add_text_block(text_widget, "Trained Words", self.civit.trained_words)
        self.add_text_block(text_widget, "Suggested Strength", self.civit.strength)
        self.add_text_block(text_widget, "Extra Floats", self.civit.extra_floats)
        self.add_text_block(text_widget, "Top 20 Tags", self.metadata.rec_tags)
        self.add_text_block(text_widget, "Version Description", self.civit.version_description)
        self.add_text_block(text_widget, "Model Description", self.civit.html_text)
        # self.add_text_block(text_widget, "File Metadata", self.metadata.metadata_report)
        self.add_collapsible_end_block(text_widget, button_frame, "File Metadata", self.metadata.metadata_report)
        text_widget.config(state="normal")

    def build_fallback_window(self, error):
        self.master.title(self.file_path)
        default_height = 400
        default_width = 800
        self.master.geometry(f"{default_width}x{default_height}")
        self.master.resizable(True, True)
        self.master.bind("<Escape>", self.close_window)
        self.master.bind("<Control-w>", self.close_window)
        self.master.grid_rowconfigure(0, weight=10, minsize=1)
        self.master.grid_rowconfigure(1, weight=0)
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_columnconfigure(1, weight=0)
        text_frame = Frame(self.master, height=1)
        text_frame.grid(row=0, column=0, sticky="nsew")
        text_frame.grid_rowconfigure(0, weight=0, minsize=1)
        text_frame.grid_columnconfigure(0, weight=1)
        text_frame.grid_propagate(False)
        text_widget = tk.Text(text_frame, wrap="word")
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")
        text_widget.pack(fill="both", expand=True)
        text_widget.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=text_widget.yview)
        button_frame = tk.Frame(self.master, height=25)
        button_frame.grid(row=2, column=0, sticky="s")
        self.add_text_block(text_widget, "Error", f"{error}")
        self.add_text_block(text_widget, "Model Hash", self.metadata.safetensors_hash)
        self.add_ez_copy(text_widget)
        self.add_text_block(text_widget, "Top 20 Tags", self.metadata.rec_tags)
        self.add_collapsible_end_block(text_widget, button_frame, "File Metadata", self.metadata.metadata_report)
        text_widget.config(state="normal")

    def on_mousewheel(self, event, widget):
        widget.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_shift_mousewheel(self, event, widget):
        widget.xview_scroll(int(-1 * (event.delta / 120)), "units")

    def open_url(self, url):
        webbrowser.open_new(url)

    def add_text_block(self, text_widget: tk.Text, display_title, display_text):
        text_title = f"{display_title}:"
        text_body = f"\n{display_text}\n\n"
        title_tag = "border_text"
        text_widget.insert(tk.END, text_title, title_tag)
        text_widget.tag_config(title_tag, border=10, borderwidth=1, relief="solid")
        tag_name = f"text_block"
        text_widget.insert(tk.END, text_body, tag_name)
        text_widget.tag_config(tag_name, lmargin1=20, lmargin2=20)

    def add_collapsible_end_block(self, text_widget: tk.Text, button_frame, display_title, display_text):
        text_title = f"{display_title}:"
        text_body = f"\n{display_text}\n\n"
        title_tag = "border_text"
        text_widget.insert(tk.END, text_title, title_tag)
        text_widget.tag_config(title_tag, border=10, borderwidth=1, relief="solid")
        collapsible_start = text_widget.index("end-1c")
        tag_name = f"collapsible_block"
        text_widget.mark_set(f"{tag_name}_start", collapsible_start)
        text_widget.tag_config(tag_name, lmargin1=20, lmargin2=20)
        button = tk.Button(
            button_frame, text="Expand Section", command=lambda x=text_widget: self.toggle_collapsible_section(x)
        )
        button.pack(pady=2)
        self.collapsible_section = {
            "collapsible_tag": tag_name,
            "collapsible_text": text_body + "\n",
            "is_collapsed": True,
            "button": button,
        }

    def toggle_collapsible_section(self, text_widget: tk.Text):
        """
        Toggle the visibility of the collapsible section.
        :param section_index: The index of the section in the sections list.
        """
        section = self.collapsible_section
        text_widget.config(state="normal")

        collapsible_tag = section["collapsible_tag"]
        start_mark = f"{collapsible_tag}_start"

        if section["is_collapsed"]:
            start_index = text_widget.index(start_mark)
            text_widget.insert(start_index, section["collapsible_text"], collapsible_tag)
            section["is_collapsed"] = False
        else:
            ranges = text_widget.tag_ranges(collapsible_tag)
            if ranges:
                text_widget.delete(ranges[0], ranges[1])
            section["is_collapsed"] = True
        button: tk.Button = section["button"]
        button.config(text="Collapse Section" if not section["is_collapsed"] else "Expand Section")

    def add_hyperlink(self, text_widget: tk.Text, version_id, model_id, display_text):
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
        self.master.bind("<space>", click)

    def add_ez_copy(self, text_widget: tk.Text):
        dict_template = ensure_double_backslashes(self.dict_entry())

        def click(event: tk.Event):
            logger.debug(f"Event state: {event.state}")
            if event.state & 0x0004:  # Control key
                text = pyperclip.paste()
                logger.debug(f"Clipboard content: {text}")
            else:
                text = ""
                logger.debug("Starting with empty string")

            text += f"\t{dict_template}\n"
            logger.debug(f"Final text: {text}")

            pyperclip.copy(text)
            return "break"

        tag_name = "ez_copy"
        title_tag = "border_text"
        text_widget.insert(tk.END, "Dictionary Template:", title_tag)
        text_widget.insert(tk.END, "\n")
        text_widget.tag_config(title_tag, border=10, borderwidth=1, relief="solid")

        text_widget.insert(tk.END, dict_template, tag_name)
        text_widget.tag_config(tag_name, foreground="blue", underline=True)
        text_widget.tag_bind(tag_name, "<Enter>", lambda e: text_widget.config(cursor="hand2"))
        text_widget.tag_bind(tag_name, "<Leave>", lambda e: text_widget.config(cursor=""))
        text_widget.tag_bind(tag_name, "<Button-1>", click)
        text_widget.insert(tk.END, "\n\n")
        self.master.bind("<`>", click)

    def close_window(self, event=None):
        self.civit and self.civit.close_sessions()
        self.master.destroy()

    # region GUI Logic

    def create_collage(self, images, cols=4, thumbnail_size=(400, 400)):
        if not images:
            logging.error("No images to create a collage.")
            return None
        rows = (len(images) + cols - 1) // cols  # Ceiling division
        thumb_width, thumb_height = thumbnail_size
        collage_width = cols * thumb_width
        collage_height = rows * thumb_height
        collage = Image.new("RGB", (collage_width, collage_height), (255, 255, 255))
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

    def dict_entry(self):
        only_1_extra_float = (
            self.civit.extra_floats
            and len(self.civit.extra_floats) <= 3
            and len(self.civit.extra_floats.split(",")) == 1
        )

        template = (
            f'"'
            + f"{self.metadata.lora_key}"
            + '": {"POSITIVE": "'
            + f'{self.civit.trained_words if self.civit.trained_words else ""}'
            + '", "WEIGHT": "'
            + f'{self.civit.strength if self.civit.strength else (self.civit.extra_floats if self.civit.extra_floats and len(self.civit.extra_floats) < 4 else "1.0")}'
            + f'", "NEGATIVE": "", "NULLIFIERS": "","NOTES":"{"" if only_1_extra_float else self.civit.extra_floats}{self.metadata.store_tags}"}},'
        )
        return template


# region Web


class Civit:
    NUM_SESSIONS = 2

    def __init__(self):
        self.data = None  # "versionID", "modelId","description", "modelName","trainedWords","imageUrls"
        self.model_id = None
        self.api_json = None
        self.html_text = None
        self.trained_words = None
        self.model_name = None
        self.base_model_name = None
        self.version_description = None
        self.strength = None
        self.image_urls = []
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
        self.api_json = self._fetch_hash_api_json(safetensors_hash)
        self.data = self._extract_model_data(
            self.api_json
        )  # "versionID", "modelId","version_description", "modelName","trainedWords","imageUrls"
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_html = executor.submit(self._fetch_model_page_html)
            future_creator_name = executor.submit(self._fetch_creator_name, self.model_id)
            future_images = executor.submit(self._fetch_images_concurrently, self.image_urls, executor)
            self.creator_name = future_creator_name.result()
            self.html_text, self.strength = future_html.result()
            self.images = future_images.result()
        self.extra_floats = self._pull_floats()

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
                # logging.info(f"Successfully fetched image {i+1}/{len(image_urls)}")
            else:
                logger.warning(f"Failed to fetch image {i+1}/{len(image_urls)}")
        return images

    def _fetch_image(self, url, thumbnail_size=(400, 400)):
        session = self.session_pool.get()
        try:
            response = session.get(url)
            response.raise_for_status()  # Raise an HTTPError for bad responses
            image = Image.open(BytesIO(response.content))
            image.thumbnail(thumbnail_size, Image.BICUBIC)
            return image

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
        finally:
            self.session_pool.put(session)

    def _fetch_hash_api_json(self, safetensors_hash):
        url = API_URL_HASH_PREFIX + str(safetensors_hash)
        session = self.session_pool.get()
        try:
            response = session.get(url)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Failed to load api_json from {url}: {e}")
            return ""
        finally:
            self.session_pool.put(session)

    def _fetch_creator_name(self, model_id):
        url = API_URL_MODELS_PREFIX + str(model_id)
        session = self.session_pool.get()
        try:
            response = session.get(url)
            response.raise_for_status()  # Check if the request was successful
            # soup = BeautifulSoup(response.text, "html.parser")
            # text = soup.get_text(separator="\n", strip=True)
            creator_name = self._extract_model_data(response.text, False).get("creator_name")
            return creator_name
        except Exception as e:
            logger.error(f"Failed to load api_json from {url}: {e}")
            return ""
        finally:
            self.session_pool.put(session)

    def _fetch_model_page_html(self):
        if not self.model_id or not self.version_id:
            return "", ""
        cookies = RequestsCookieJar()
        cookies.set("__Secure-civitai-token", access_cookie)
        # cookies.set("stripe_mid", stripe_mid)
        # cookies.set("cf_clearance", cf_clearance)
        # cookies.set("ph_phc_MRWB5oArnYNY437MmczkYEQ6qWydDqsq1NqzpFjg8OI_posthog", ph_phc_MRWB5oArnYNY437MmczkYEQ6qWydDqsq1NqzpFjg8OI_posthog)
        # cookies.set("__Host-next-auth.csrf-token", csrf)
        # cookies.set("__Secure-next-auth.callback-url", Secure)
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        }
        model_url = MODEL_PAGE_URL_PREFIX + self.model_id + MODEL_PAGE_VERSION_PREFIX + self.version_id
        session: requests.Session = self.session_pool.get()
        try:
            response = session.get(model_url, headers=headers, cookies=cookies)
            response.raise_for_status()  # Check if the request was successful
            html_doc = Document(response.text)
            match = re.search(
                r'<span class="mantine-h9iq4m mantine-Badge-inner">Strength: (\d\.\d)</span>', response.text
            )
            strength_result = match.group(1) if match else ""
            return (self.html_to_markdown(html_doc.summary()), strength_result)
        except Exception as e:
            logger.error(f"Failed to load html from {model_url}: {e}")
            return ("", "")
        finally:
            self.session_pool.put(session)

    def _pull_floats(self):
        floats_string = ""
        # removal_pattern = r'cfg.+'
        # sani_html = re.sub(removal_pattern, "", self.html_text, 0, re.IGNORECASE)
        targeting_pattern = r"weight.+"
        target_matches = re.findall(targeting_pattern, self.html_text, re.IGNORECASE)
        reconstructed_html = "\n".join(target_matches)
        pattern = r"(?<!\()-?\d+(?:\.\d+)?(?:\s*[-to]+\s*\d+(?:\.\d+)?)?(?!\))"
        matches = re.findall(pattern, reconstructed_html, re.IGNORECASE)
        floats_list = [" ".join(match) for match in map(str.split, matches)]
        if len(floats_list) > 1:
            floats_string = f"<{ ', '.join(floats_list)}>, "
        else:
            floats_string = self.safe_float_range_to_average_string(floats_list)
        return floats_string

    def safe_float_range_to_average_string(self, floats_list: list):
        float_pre_string = "".join(floats_list)
        try:
            float_range_list = re.split(r"to|-^\d", float_pre_string)
            float_range_list = list(map(self.safe_float, map(str.strip, float_range_list)))
            min_of_range = min(float_range_list)  # round((float_range_list[0] + float_range_list[1]) / 2, 1)
            floats_string = str(min_of_range)
            if not self.is_numeric_string(floats_string):
                raise ValueError
        except Exception as e:
            floats_string = ""
        return floats_string

    @staticmethod
    def is_numeric_string(input_str):
        return re.match(r"^-?\d+(\.\d+)?$", input_str.strip()) is not None

    def safe_float(self, x):
        if isinstance(x, float):
            return x
        elif isinstance(x, int):
            return float(x)
        elif self.is_numeric_string(x):
            return float(x)
        else:
            return 1.0

    def close_sessions(self):
        for session in self.sessions:
            session.close()

    def _extract_model_data(self, json_data, hashed=True):
        if not json_data:
            return {}

        # def clean_json(json_str):
        #     json_str = re.sub(r"[\x00-\x1F\x7F]", "", json_str)
        #     return json_str

        if isinstance(json_data, str):
            json_data = json.loads(sanitize_json_string(json_data))

        if hashed:
            # AliRecursiveJSONLoader(json_data)
            # logger.debug(json.dumps(json_data, indent=2))
            extracted_data = {
                "modelId": None,
                "versionId": None,
                "modelName": "",
                "baseModel": "",
                "trainedWords": [],
                "version_description": "",
                "imageUrls": [],
            }
            if "id" in json_data:
                extracted_data["versionId"] = json_data["id"]
            if "modelId" in json_data:
                extracted_data["modelId"] = json_data["modelId"]
            if "description" in json_data:
                extracted_data["version_description"] = json_data["description"]
            if "model" in json_data:
                model_name = json_data["model"]["name"]
                if "name" in json_data:
                    model_name += f" - {json_data['name']}"
                extracted_data["modelName"] = model_name
            if "baseModel" in json_data:
                extracted_data["baseModel"] = json_data["baseModel"]
            if "trainedWords" in json_data:
                extracted_data["trainedWords"] = json_data["trainedWords"]
            if "images" in json_data and isinstance(json_data["images"], list):
                for image in json_data["images"]:
                    if "url" in image and "type" in image and image["type"] != "video":
                        extracted_data["imageUrls"].append(image["url"])
            self.version_id = str(extracted_data["versionId"])
            self.model_id = str(extracted_data["modelId"])
            self.model_name = str(extracted_data["modelName"])
            self.base_model_name = str(extracted_data["baseModel"])
            tidy_trained_phrases: list = list(map(tidy_tags, extracted_data["trainedWords"]))
            self.trained_words = f"{', '.join(tidy_trained_phrases)}"
            self.version_description = str(extracted_data["version_description"])
            self.image_urls = extracted_data["imageUrls"]
            return extracted_data
        else:
            extracted_data = {
                "creator_name": None,
            }
            if "creator" in json_data and "username" in json_data["creator"]:
                extracted_data["creator_name"] = json_data["creator"]["username"]
            self.creator_name = extracted_data["creator_name"]
            return extracted_data


# region Safetensors


class Safetensors:
    def __init__(self):
        self.file_handle = None  # file handle
        self.header_byte_buffer = None  # header byte buffer
        self.header = None  # parsed header as a dict
        self.sha_hash = 0

    def __del__(self):
        self.close_file()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close_file()

    @staticmethod
    def get_file(filename: str, quiet=False, parseHeader=True):
        safetensor: Safetensors = Safetensors()
        safetensor._open(filename, quiet, parseHeader)
        return safetensor

    def _open(self, file_name: str, quiet=False, parseHeader=True) -> int:
        file_stats = os.stat(file_name)
        if file_stats.st_size < 8:
            raise SafetensorsException.invalid_file(file_name, "Length less than 8 bytes")
        with open(file_name, "rb") as file_handle:
            self.sha_hash = retrieve_sha256_hash(file_name)
        with open(file_name, "rb") as file_handle:
            b8 = file_handle.read(8)  # read header size
            if len(b8) != 8:
                raise SafetensorsException.invalid_file(file_name, f"Read only {len(b8)} bytes at start of file")
            header_length = int.from_bytes(b8, "little", signed=False)
            if 8 + header_length > file_stats.st_size:
                raise SafetensorsException.invalid_file(file_name, "Header extends past end of file")
            header_byte_buffer = file_handle.read(header_length)
            if len(header_byte_buffer) != header_length:
                raise SafetensorsException.invalid_file(
                    file_name, f"header size is {header_length}, but read {len(header_byte_buffer)} bytes"
                )
            self.filename = file_name
            self.file_stats = file_stats
            self.file_handle = file_handle
            self.header_byte_buffer = header_byte_buffer.decode("utf-8")
            self.header_length = header_length
            if not quiet:
                logger.info(
                    f"{self.filename}: length={self.file_stats.st_size}, header length={self.header_length}, byte buffer={self.header_byte_buffer}"
                )
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
            self.file_handle = None
            self.filename = ""

    def _CheckDuplicateHeaderKeys(self):
        def parse_object_pairs(pairs):
            return [k for k, _ in pairs]

        keys = json.loads(self.header_byte_buffer, object_pairs_hook=parse_object_pairs)
        header_duplicate_check = {}
        for k in keys:
            if k in header_duplicate_check:
                header_duplicate_check[k] = header_duplicate_check[k] + 1
            else:
                header_duplicate_check[k] = 1
        hasError = False
        for k, v in header_duplicate_check.items():
            if v > 1:
                logger.error(f"key {k} used {v} times in header", file=sys.stderr)
                hasError = True
        if hasError:
            raise SafetensorsException.invalid_file(self.filename, "Duplicate keys in header")


# region Metadata


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
    pretty_metadata : str
        A formatted version of the metadata json for easier human readability.
    """

    def __init__(self):
        self.file_path: str = ""
        self.safetensors_file: Safetensors = None
        self.safetensors_hash: str = ""
        self.header = None
        self.metadata_dict: str = ""
        self.metadata_report: str = ""
        self.lora_key: str = ""
        self.rec_tags: str = ""
        self.store_tags: str = ""
        self.pretty_metadata: str = ""

    @staticmethod
    def get_metadata(file_path):
        metadata_handler: Metadata = Metadata()
        metadata_handler._process_metadata(file_path)
        return metadata_handler

    def _process_metadata(self, file_path):
        self.file_path = file_path
        self.safetensors_file = self._get_safetensors_file(self.file_path)
        self.safetensors_hash = self.safetensors_file.get_hash()
        self.header = self.safetensors_file.get_header()
        self.metadata_report = self._get_implicit_metadata_report(self.header)
        self.lora_key = self.format_lora_filepath_to_keyname()

    def _get_safetensors_file(self, file_path, quiet=True):
        safetensors_file = Safetensors.get_file(file_path, quiet)  # omits the first non-JSON line
        return safetensors_file

    def _get_implicit_metadata_report(self, header: dict, tag_count=20):
        metadata = header.get("__metadata__", {})
        full_sorted_tag_dict_list = self.find_tag_frequencies(metadata)
        full_sorted_tag_string = "\n\n".join(full_sorted_tag_dict_list)
        AliRecursiveJSONLoader(metadata)
        pretty_metadata = json.dumps(metadata, ensure_ascii=False, separators=(", ", ": "), indent=2)
        # ss_tag_frequency: str|bytes|bytearray = metadata.get("ss_tag_frequency", {})
        # ss_tag_frequency_dict: dict = next(iter(ss_tag_frequency.values()), {})
        # filtered_tags = self._get_filtered_tags(ss_tag_frequency_dict)
        metadata_report = ""
        if full_sorted_tag_string:
            rec_tags = self._get_top_tags(full_sorted_tag_dict_list, tag_count)
            store_tags = self._get_top_tags(full_sorted_tag_dict_list, 10)
            # pretty_top_tags = json.dumps(rec_tags, ensure_ascii=False, separators=(', ', ': '), indent=0)
            # pretty_top_tags = pretty_top_tags.strip("{} \n")
            metadata_report = f"Full Tag List:\n{full_sorted_tag_string}\n\nMetadata:\n{pretty_metadata}"
            self.store_tags = tidy_tags(ensure_double_backslashes(store_tags))
            self.rec_tags = tidy_tags(ensure_double_backslashes(rec_tags))
        else:
            metadata_report = f"No implicit tag information\n\nMetadata:\n{pretty_metadata}"
        # logger.debug(f"::::{pretty_metadata}")
        self.metadata_dict = metadata
        self.pretty_metadata = pretty_metadata
        return metadata_report

    def find_tag_frequencies(self, input_dict):
        """
        Recursively search for 'tag_frequency' or 'ss_tag_frequency' in a dictionary.
        Return the first value found, sorted and stringified.

        Parameters
        input_dict: Dictionary to search.
        """
        out_list = []

        def recursive_search(d):
            for key, value in d.items():
                if key == "tag_frequency" or key == "ss_tag_frequency":
                    if isinstance(value, str):
                        try:
                            value = json.loads(value)
                        except:
                            continue
                    for k, v in value.items():
                        if len(v):
                            sorted_v = dict(sorted(v.items(), key=lambda x: int(x[1]), reverse=True))
                            out_list.append(json.dumps(sorted_v, indent=2))
                if isinstance(value, dict):
                    recursive_search(value)

        recursive_search(input_dict)
        if len(out_list):
            return out_list
        return ""  # Neither key found

    def format_lora_filepath_to_keyname(self):
        lora_path = self.file_path
        if not lora_path:
            return ""
        if not isinstance(lora_path, str):
            try:
                lora_path = str(lora_path)
            except:
                return ""
        lora_path = lora_path.replace("\\", "/")
        lora_path = lora_path.strip("<>")
        lora_sans_lora_prefix = re.sub(r"lora:", "", lora_path)
        minus_drive = os.path.splitdrive(lora_sans_lora_prefix)[-1]
        clean_lora_path = re.sub(r":.*$", "", minus_drive)
        lora_sans_path_prefix = os.path.basename(clean_lora_path)
        lora_sans_model_prefix = re.sub(r".*(XL_|SD15_|Flux1D_|Flux1S_)", "", lora_sans_path_prefix)
        lora_name_only = os.path.splitext(lora_sans_model_prefix)[0]
        return lora_name_only

    def _get_top_tags(self, full_sorted_tag_dict_list: str, amount: int):
        if amount <= 0:
            return ""
        try:
            dict = json.loads(full_sorted_tag_dict_list[0])
        except:
            return "_get_top_tags: Stringify failed."
        keys = list(dict.keys())[:amount]
        return ",".join(keys)

    def _get_filtered_tags(self, ss_tag_frequency_dict: dict):
        def filter_above_percentile(ss_tag_frequency_dict, percentile: float) -> dict:
            values = list(ss_tag_frequency_dict.values())
            # Compute the percentile threshold
            threshold = np.percentile(values, percentile)
            filtered_data = {k: v for k, v in ss_tag_frequency_dict.items() if v >= threshold}
            return filtered_data

        def sort_dict_by_values(data: dict) -> dict:
            sorted_items = sorted(data.items(), key=lambda item: item[1], reverse=True)
            sorted_dict = {k: v for k, v in sorted_items}
            return sorted_dict

        if ss_tag_frequency_dict:
            tag_count = len(ss_tag_frequency_dict.items())
            match tag_count:
                # case tag_count if tag_count > 500:
                #     filtered_ss_tag_frequency_dict = filter_above_percentile(ss_tag_frequency_dict,99)
                # case tag_count if tag_count > 250:
                #     filtered_ss_tag_frequency_dict = filter_above_percentile(ss_tag_frequency_dict,97)
                # case tag_count if tag_count > 100:
                #     filtered_ss_tag_frequency_dict = filter_above_percentile(ss_tag_frequency_dict,95)
                # case tag_count if tag_count > 50:
                #     filtered_ss_tag_frequency_dict = filter_above_percentile(ss_tag_frequency_dict,90)
                # case tag_count if tag_count > 20:
                #     filtered_ss_tag_frequency_dict = filter_above_percentile(ss_tag_frequency_dict,50)
                case _:
                    filtered_ss_tag_frequency_dict = ss_tag_frequency_dict
            # sorted_ss_tag_frequency_dict = sort_dict_by_values(filtered_ss_tag_frequency_dict)
            # AliRecursiveJSONLoader(sorted_ss_tag_frequency_dict)
            sorted_filtered_ss_tag_frequency_dict = sort_dict_by_values(filtered_ss_tag_frequency_dict)
            AliRecursiveJSONLoader(sorted_filtered_ss_tag_frequency_dict)
            return sorted_filtered_ss_tag_frequency_dict
        return None


# region Helpers


def retrieve_sha256_hash(
    file_path, ads_stream_name="sha256", create_alternate_data_stream=True, create_hash_file=False, force_compute=False
):
    def compute_hash(file_path, create_alternate_data_stream, create_hash_file):
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
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

    def write_hash_ADS(
        file_path,
        stream_value,
        stream_name=ads_stream_name,
    ):
        ads_path = f"{file_path}:{stream_name}"
        try:
            with open(ads_path, "w") as ads:
                ads.write(stream_value)
        except Exception as e:
            logger.error(f"Error setting alternate data stream on file {ads_path}: {e}")

    def read_hash_ADS(file_path, stream_name):
        ads_path = f"{file_path}:{stream_name}"
        try:
            with open(ads_path, "r") as ads:
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


def tidy_tags(tag_string):
    if isinstance(tag_string, list):
        tag_string = ", ".join(map(str, tag_string))
    if not isinstance(tag_string, str) or tag_string.strip(" ,\t\r\n") == "":
        return ""
    normalized_tags = [t.lower() for t in map(str.strip, tag_string.split(",")) if t]
    processed_tag_string = re.sub(r"\s+", " ", ", ".join(normalized_tags))
    return processed_tag_string


def sanitize_json_string(json_str):
    """
    Attempts to sanitize a raw JSON string so it can be safely loaded.
    - Removes non-printable control characters.
    - Fixes JSON keys by stripping characters that might cause parsing issues.
    - Returns a valid JSON string if successful, or None on failure.
    """
    if not isinstance(json_str, str) or not json_str.strip():
        print("Error: Input must be a non-empty string.")
        return None
    # Step 1: Remove control characters (but leave standard whitespace)
    sanitized = re.sub(r"[\x00-\x1F\x7F]", "", json_str)

    # Try to load the JSON. If it works, return a cleaned version.
    try:
        obj = json.loads(sanitized)
        return json.dumps(obj, indent=2)
    except json.JSONDecodeError:
        pass

    # Step 2: Fix problematic keys.
    # This regex finds keys enclosed in double quotes and attempts to remove illegal characters.
    def fix_key(match):
        key = match.group(1)
        # Remove characters except word chars, whitespace, dash, underscore, period.
        fixed_key = re.sub(r"[^\w\s\-_.]", "", key)
        return f'"{fixed_key}":'

    sanitized = re.sub(r'"([^"]+)"\s*:', fix_key, sanitized)

    # Step 3: Attempt to load the JSON again.
    try:
        obj = json.loads(sanitized)
    except json.JSONDecodeError as e:
        print(f"Error at line {e.lineno}, column {e.colno}: {e.msg}")
        # start = max(e.pos - 50, 0)
        # end = e.pos + 500
        # logger.debug("Context: %s" % sanitized[start:end])


def ensure_double_backslashes(text):
    text = re.sub(r"\\*\(", r"\\\\(", text)
    text = re.sub(r"\\*\)", r"\\\\)", text)
    return text


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
    # s = time.time()
    app = MetadataGUI(root, file_path)
    # print("e:", time.time() - s)
    root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        main(file_path)
    else:
        # TEST_FILE_PATH = r"s:\SD_Archive\models\Lora\PONY\Style_In\Pony_XL_Orenji_3_Style.safetensors"
        TEST_FILE_PATH = r"C:\Users\alist\Downloads\ILL_Waterkuma_2_Style.safetensors"
        main(TEST_FILE_PATH)
