import sys
import os
import json
import requests
import re
import webbrowser
import logging
from bs4 import BeautifulSoup
import hashlib
def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    with open(os.path.splitext(os.path.abspath(__file__))[0] + "_uncaught_error.log","w") as f:
        f.write(f"{exc_type}\n{exc_value}\n{exc_traceback}")
sys.excepthook = handle_uncaught_exception


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

# parent_dir = os.path.abspath(log_file_path) # Start with the current working directory
# while not os.path.basename(parent_dir) == "AliNodes": # Keep moving up until the directory ends with "AliNodes" or root is reached
#     new_parent_dir = os.path.abspath(os.path.join(parent_dir, "..")) # Move up one directory level
#     if new_parent_dir == parent_dir: # If we've reached the root directory (no more directories to go up)
#         raise FileNotFoundError("The 'AliNodes' directory was not found in the path.")
#     parent_dir = new_parent_dir
# sys.path.append(parent_dir)
# os.chdir(parent_dir)

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


api_url_prefix = "https://civitai.com/api/v1/model-versions/by-hash/"
model_page_url_prefix = "https://civitai.com/models/"
def context_menu_execute(file_path=""):
	if not (model_hash := retrieve_sha256_hash(file_path)):
		return None
	
	model_id = None
	
	url = f"{api_url_prefix}{model_hash}"

	try:
		response = requests.get(url)
		response.raise_for_status()  # Check if the request was successful
		soup = BeautifulSoup(response.text, 'html.parser')
		model_json = soup.get_text(separator='\n', strip=True)
	except Exception as e:
		logging.error("Exception occurred", exc_info=True)
		print(f"Failed to load json from {url}: {e}")
		return
	
	if not model_json:
		return
	
	if isinstance(model_json, str):
		model_json = json.loads(re.sub(r'[\x00-\x1F\x7F]', '', model_json))

	if 'modelId' in model_json:
		model_id = model_json["modelId"]

	if model_id:
		model_url = f"{model_page_url_prefix}{model_id}"
		webbrowser.open_new(model_url)

   
if __name__ == "__main__":
	if len(sys.argv) > 1:
		file_path = sys.argv[1]
		context_menu_execute(file_path)
	#context_menu_execute("s:\A1111\models\Stable-diffusion\Pony_XL_SatPonyJourney_v1_Ckpt.safetensors")
