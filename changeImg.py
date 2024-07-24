from PIL import Image
import numpy as np
import os


def transform_color(input_image, mat):
    return input_image @ mat.T


def changeColor(rgb, type="p"):
    deu_mat = np.array([[1, 0, 0], [1.101, 0, -0.0090], [0, 0, 1]], dtype=np.float16)
    prot_mat = np.array([[0, 0.908, 0.00819], [0, 1, 0], [0, 0, 1]], dtype=np.float16)
    trit_mat = np.array([[1, 0, 0], [0, 1, 0], [-0.1577, 1.195, 0]], dtype=np.float16)

    rgbTolms = np.array([[0.390, 0.5499, 0.00890], [0.0709, 0.963, 0.00136], [0.0231, 0.128, 0.936]], dtype=np.float16)
    lmsTorgb = np.array([[2.858, -1.62870, -0.0248], [-0.21043, 1.158, 0.000320], [-0.04189, -0.118154, 1.0689]],
                        dtype=np.float16)
    arr_lms = transform_color(rgb, rgbTolms)

    if type == 'p':
        arr_lms_after = transform_color(arr_lms, prot_mat)
    elif type == 'd':
        arr_lms_after = transform_color(arr_lms, deu_mat)
    elif type == 't':
        arr_lms_after = transform_color(arr_lms, trit_mat)
    else:
        print("Wrong Type!")

    result = transform_color(arr_lms_after, lmsTorgb)
    return result


def arrayToImg(arr):
    arr = inverse_gamma(arr, 2.2)
    arr = rgb_array(arr)
    arr = arr.astype('uint8')
    img = Image.fromarray(arr, mode='RGB')
    return img


def rgb_array(arr, min=0, max=255):
    arr2 = np.ones_like(arr)
    arr = np.maximum(arr2 * min, arr)
    arr = np.minimum(arr2 * max, arr)
    return arr


def gamma(rgb, gamma_value):
    srgb = np.zeros_like(rgb, dtype=np.float16)
    for i in range(3):
        idx = rgb[:, :, i] > 0.04045 * 255
        srgb[idx, i] = ((rgb[idx, i] / 255 + 0.055) / 1.055) ** gamma_value
        idx = np.logical_not(idx)
        srgb[idx, i] = rgb[idx, i] / 255 / 12.9
    return srgb


def inverse_gamma(srgb, gamma_value):
    rgb = np.zeros_like(srgb, dtype=np.float16)
    for i in range(3):
        idx = srgb[:, :, i] <= 0.00313
        rgb[idx, i] = 255 * 12.92 * srgb[idx, i]
        idx = np.logical_not(idx)
        rgb[idx, i] = 255 * (1.055 * srgb[idx, i] ** (1 / gamma_value) - 0.055)

    return rgb


def changeImage(image, username, filename):
    # Ensure directories exist
    base_dirs = ['static/images/normal', 'static/images/protanopia', 'static/images/deuteranopia',
                 'static/images/tritanopia']
    for base_dir in base_dirs:
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)

    # Load and process the image
    img = np.asarray(Image.open(image).convert("RGB"), dtype=np.float16)
    img = gamma(img, 2.2)

    # Save the normal image
    normal_img = arrayToImg(img)
    normal_img.save(f"static/images/normal/{username}_n_{filename}")

    # Process and save protanopia image
    arr_result = changeColor(img, 'p')
    img_result = arrayToImg(arr_result)
    img_result.save(f"static/images/protanopia/{username}_p_{filename}")

    # Process and save deuteranopia image
    arr_result = changeColor(img, 'd')
    img_result = arrayToImg(arr_result)
    img_result.save(f"static/images/deuteranopia/{username}_d_{filename}")

    # Process and save tritanopia image
    arr_result = changeColor(img, 't')
    img_result = arrayToImg(arr_result)
    img_result.save(f"static/images/tritanopia/{username}_t_{filename}")
