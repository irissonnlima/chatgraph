import hashlib
import base64
from chatgraph.types.message_types import Message


class ImageData:
    def __init__(self, url: str, image_bytes: bytes = None):
        if not url and not image_bytes:
            raise ValueError("URL or image bytes must be provided.")

        self.url = url
        self.image_bytes = image_bytes

        # Create hash of image bytes if available, otherwise use URL
        hash_input = image_bytes if image_bytes else url.encode("utf-8")

        # Create SHA-256 hash and encode in base64
        self.image_id = base64.b64encode(hashlib.sha256(hash_input).digest()).decode(
            "utf-8"
        )


class SendImage:
    def __init__(self, image: ImageData, message: Message):
        if not isinstance(image, ImageData):
            raise TypeError("Expected an instance of ImageData.")

        self.type = "image"
        self.image = image
        self.message = message

    def to_dict(self):
        return {
            "file_id": self.image.image_id,
            "message": self.message.to_dict(),
        }
