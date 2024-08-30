import cv2
from utils import ImageObject
from slid import pSLID, SLID, slid_tendency
from laps import LAPS
from llr import LLR, llr_pad

NC_LAYER = 0
NC_IMAGE = object

NC_CONFIG = {'layers': 3}
def detect_chessboard(input_path, output_path):
    # Load the input image
    input_image = cv2.imread(input_path)

    # Initialize variables
    NC_IMAGE, NC_LAYER = ImageObject(input_image), 0

    # Loop through the layers based on NC_CONFIG['layers']
    for _ in range(NC_CONFIG['layers']):
        NC_LAYER += 1
        
        # Step 1: Find all possible lines using SLID algorithm
        segments = pSLID(NC_IMAGE['main'])
        raw_lines = SLID(NC_IMAGE['main'], segments)
        lines = slid_tendency(raw_lines)

        # Step 2: Find interesting intersections using LAPS algorithm
        points = LAPS(NC_IMAGE['main'], lines)

        # Step 3: Reproduction of last layer for chessboard corners using LLR algorithm
        inner_points = LLR(NC_IMAGE['main'], points, lines)
        four_points = llr_pad(inner_points, NC_IMAGE['main'])

        # Crop the image based on the four_points
        try:
            NC_IMAGE.crop(four_points)
        except:
            print("Unable to crop using LLR, proceeding with inner points")
            NC_IMAGE.crop(inner_points)

        # Save the cropped image
        cv2.imwrite(output_path, NC_IMAGE['orig'])
    
    print("Detection completed. Output saved to:", output_path)
