import os

def get_all_images(image_dir):
    """
    Return a sorted list of image file paths (relative to image_dir).
    Includes common image formats only.
    """
    images = []
    for root, _, files in os.walk(image_dir):
        for f in files:
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                rel_path = os.path.relpath(os.path.join(root, f), image_dir)
                images.append(rel_path.replace("\\", "/"))
    return sorted(images)
