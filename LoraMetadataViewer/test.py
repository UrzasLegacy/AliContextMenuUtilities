from readability import Document
import requests

response = requests.get("https://civitai.com/models/748074")
doc = Document(response.text)
print(doc.summary())