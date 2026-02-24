import easyocr


class OCR:
    def __init__(self):
        # Initialize EasyOCR reader with English and Indonesian languages
        self.reader = easyocr.Reader(
            ["en", "id"],
            gpu=False,
        )

    def read_text(self, image_path: str) -> str:
        """
        Read text from an image using EasyOCR.

        Args:
            image_path (str): Path to the image file.

        Returns:
            str: Extracted text from the image.
        """
        # Perform OCR on the image
        results = self.reader.readtext(image_path, detail=0)

        return results[0]
