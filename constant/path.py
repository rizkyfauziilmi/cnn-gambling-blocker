import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PROJECT_ROOT = os.path.dirname(BASE_DIR)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Root dataset folder
DATASET_DIR = os.path.join(PROJECT_ROOT, "dataset")

# Image paths
IMAGE_PATH = os.path.join(DATASET_DIR, "images")
GAMBLING_IMAGE_PATH = os.path.join(IMAGE_PATH, "gambling")
NON_GAMBLING_IMAGE_PATH = os.path.join(IMAGE_PATH, "non_gambling")

# Text paths
TEXT_PATH = os.path.join(DATASET_DIR, "texts")
GAMBLING_TEXT_PATH = os.path.join(TEXT_PATH, "gambling")
NON_GAMBLING_TEXT_PATH = os.path.join(TEXT_PATH, "non_gambling")

# CSV
MASTER_DATASET_PATH = os.path.join(DATASET_DIR, "master_dataset.csv")

# Model Output
MODEL_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "bin")
MODEL_IMAGE_OUTPUT_DIR = os.path.join(MODEL_OUTPUT_DIR, "image")
MODEL_TEXT_OUTPUT_DIR = os.path.join(MODEL_OUTPUT_DIR, "text")
EFFICIENTNET_B0_MODEL_PATH = os.path.join(MODEL_IMAGE_OUTPUT_DIR, "efficientnet_b0_gambling.pth")
MOBILENET_V3_MODEL_PATH = os.path.join(MODEL_IMAGE_OUTPUT_DIR, "mobilenet_v3_gambling.pth")
