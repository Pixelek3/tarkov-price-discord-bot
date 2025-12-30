import cv2
import numpy as np
from paddleocr import PaddleOCR
from typing import List
import logging

logger = logging.getLogger("TarkovBot.ocr")

ocr_engine = PaddleOCR(use_textline_orientation=False, lang='en')

def process_image_ocr(image_bytes: bytes) -> List[str]:
    image = np.asarray(bytearray(image_bytes), dtype="uint8")
    img = cv2.imdecode(image, cv2.IMREAD_COLOR)
    
    if img is None:
        return []

    # Upscaling 2x
    try:
        img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    except Exception:
        pass

    try:
        result = ocr_engine.ocr(img)
    except Exception as e:
        logger.error(f"OCR engine error: {e}")
        return []

    detected_texts = []

    try:
        if isinstance(result, list) and len(result) > 0:
            data = result[0]
            
            if isinstance(data, dict) and 'rec_texts' in data:
                texts = data['rec_texts']
                scores = data.get('rec_scores', [])
                
                for i, text in enumerate(texts):
                    score = scores[i] if i < len(scores) else 0.0
                    
                    if score > 0.5 and len(text) > 2:
                        detected_texts.append(text)
            
            # Fallback method
            else:
                logger.warning("Missing 'rec_texts' key, attempting fallback method...")

    except Exception as e:
        logger.error(f"Error extracting text: {e}")
        return []

    return list(set(detected_texts))