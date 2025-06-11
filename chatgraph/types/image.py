from datetime import datetime, timedelta
import hashlib
import base64
from chatgraph.types.message_types import Message


class ImageData:
    """
    Representa dados de uma imagem, seja por URL ou arquivo local. Caso fornecido um url e um caminho de arquivo, o url será utilizado.
    Atributos:
        type (str): Tipo de imagem, "link" para URL ou "file" para arquivo local.
        url (str): URL da imagem, se aplicável.
        image_path (str): Caminho do arquivo de imagem, se aplicável.
        expiration (int): Tempo de expiração em minutos, 0 para sem expiração.
    """

    def __init__(self, *, url: str = None, image_path: str = None, expiration: int = 0):

        if not url and not image_path:
            raise ValueError("URL or image path must be provided.")

        self.type = "link" if url else "file"
        self.url = url
        self.expiration = expiration

        self.image_bytes = None
        self.file_extension = None
        if self.type == "file":
            if not image_path:
                raise ValueError("Image path must be provided for file type.")
            self.file_extension = image_path.split(".")[-1]
            with open(image_path, "rb") as f:
                self.image_bytes = f.read()

        # Create hash of image bytes if available, otherwise use URL
        hash_input = self.image_bytes if self.image_bytes else url.encode("utf-8")

        # Create SHA-256 hash and encode in base64
        self.image_id = base64.b64encode(hashlib.sha256(hash_input).digest()).decode(
            "utf-8"
        )

    def get_upload_dict(self):
        dict_data = {}
        if self.expiration > 0:
            now = datetime.now()
            expiration_time = now + timedelta(minutes=self.expiration)
            dict_data["expiration"] = expiration_time.strftime("%Y-%m-%d %H:%M:%S")

        if self.type == "file":
            dict_data["file_type"] = self.type
            dict_data["file_content"] = self.image_bytes
            dict_data["file_extension"] = self.file_extension
        else:
            dict_data["file_type"] = self.type
            dict_data["file_url"] = self.url

        return dict_data

    def get_dict(self):
        dict_data = {
            "image_id": self.image_id,
            "file_type": self.type,
        }
        if self.type == "file":
            dict_data["file_content"] = self.image_bytes
            dict_data["file_extension"] = self.file_extension
        else:
            dict_data["file_url"] = self.url
        return dict_data


class ImageMessage:
    def __init__(self, image: ImageData, message: Message = None):
        if not isinstance(image, ImageData):
            raise TypeError("Expected an instance of ImageData.")

        self.type = "image"
        self.image = image
        self.message = message

    def to_dict(self):
        if not self.message:
            return {
                "file_id": self.image.image_id,
                "message": {},
            }

        return {
            "file_id": self.image.image_id,
            "message": self.message.to_dict(),
        }
