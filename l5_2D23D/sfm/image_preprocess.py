"""
Image preprocessing for SfM pipeline.
Reads images, resizes to fixed width, saves to output directory.
"""

import os
import cv2
from sfm.utils import ensure_dir, get_image_files


def preprocess_images(image_dir, output_dir, resize_width, logger=None):
    """Read all images, resize to fixed width, save to output directory.

    Args:
        image_dir: Path to input images directory.
        output_dir: Path to output resized images directory.
        resize_width: Target width in pixels.
        logger: Optional logger instance.

    Returns:
        List of image filenames processed, in order.
    """
    ensure_dir(output_dir)
    image_files = get_image_files(image_dir)

    if not image_files:
        msg = f"No image files found in {image_dir}"
        if logger:
            logger.error(msg)
        raise FileNotFoundError(msg)

    if logger:
        logger.info(f"Found {len(image_files)} images in {image_dir}")
        logger.info(f"Resizing to width={resize_width}px, saving to {output_dir}")

    for fname in image_files:
        img_path = os.path.join(image_dir, fname)
        img = cv2.imread(img_path)
        if img is None:
            if logger:
                logger.warning(f"Could not read {img_path}, skipping")
            continue

        h, w = img.shape[:2]
        new_w = resize_width
        new_h = int(round(h * resize_width / w))
        img_resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

        out_path = os.path.join(output_dir, fname)
        cv2.imwrite(out_path, img_resized)

        if logger:
            logger.debug(f"  {fname}: {w}x{h} -> {new_w}x{new_h}")

    if logger:
        logger.info(f"Preprocessed {len(image_files)} images successfully")

    return image_files
