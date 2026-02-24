import re
from logging import INFO

import easyocr

from utils.logger import get_logger


class OCR:
    def __init__(self, log_level=INFO):
        self.logger = get_logger(self.__class__.__name__, level=log_level)

        self.reader = easyocr.Reader(
            ["en", "id"],
            gpu=False,
        )

        self.logger.info("EasyOCR reader initialized with English and Indonesian languages.")

    @staticmethod
    def _sort_by_position(results):
        """
        Sort OCR result: top-to-bottom, then left-to-right
        """
        return sorted(
            results,
            key=lambda x: (
                min(point[1] for point in x[0]),  # y-axis
                min(point[0] for point in x[0]),  # x-axis
            ),
        )

    @staticmethod
    def _basic_clean(text: str) -> str:
        """
        Light cleaning only (important for judi keywords like slot88, 777, 4d, dll)
        """
        text = text.lower()
        text = re.sub(r"[^a-zA-Z0-9\s]", "", text)  # Remove all symbols and punctuation
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def read_text(
        self,
        image_path: str,
        min_conf: float = 0.65,
        label: str | None = None,
    ) -> str:
        """
        Extract OCR text and return FastText-ready string.
        """

        results = self.reader.readtext(image_path)
        self.logger.debug({"OCR results": results})

        results = self._sort_by_position(results)

        texts = []

        # Filter by confidence and clean text
        for _bbox, text, conf in results:
            if float(conf) >= min_conf:
                cleaned = self._basic_clean(text)
                if cleaned:
                    texts.append(cleaned)

        full_text = " ".join(texts)

        # supervised fasttext format
        if label:
            full_text = f"__label__{label} {full_text}"

        return full_text
