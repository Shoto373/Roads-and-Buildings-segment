import os
import cv2
import numpy as np
import torch
import albumentations as album
import segmentation_models_pytorch as smp
import matplotlib.pyplot as plt
from tqdm import tqdm

def colour_code_segmentation(image, label_values):
    colour_codes = np.array(label_values)
    x = colour_codes[image.astype(int)]
    return x

class_names = ['background', 'building']
class_rgb_values = [[0, 0, 0], [255, 255, 255]]
select_class_rgb_values = np.array(class_rgb_values)

DATA_DIR = os.path.join('notebooks', 'input', 'massachusetts-buildings-dataset', 'tiff')
x_test_dir = os.path.join(DATA_DIR, 'test')
y_test_dir = os.path.join(DATA_DIR, 'test_labels')

image_paths = [os.path.join(x_test_dir, image_id) for image_id in sorted(os.listdir(x_test_dir))]
mask_paths = [os.path.join(y_test_dir, image_id) for image_id in sorted(os.listdir(y_test_dir))]

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = torch.load('weights/best_model.pth', map_location=DEVICE, weights_only=False)
model.eval()

test_transform = album.Compose([
    album.PadIfNeeded(min_height=1536, min_width=1536, border_mode=0),
])

def to_tensor(x, **kwargs):
    return x.transpose(2, 0, 1).astype('float32')

preprocessing_fn = smp.encoders.get_preprocessing_fn('efficientnet-b7', 'imagenet')

def crop_image(img, target_size=1500):
    padding = (img.shape[0] - target_size) // 2
    if padding == 0:
        return img
    return img[padding:-padding, padding:-padding]

for idx in tqdm(range(min(10, len(image_paths))), desc="Generating Examples"):
    image = cv2.cvtColor(cv2.imread(image_paths[idx]), cv2.COLOR_BGR2RGB)
    mask = cv2.cvtColor(cv2.imread(mask_paths[idx]), cv2.COLOR_BGR2RGB)

    padded_sample = test_transform(image=image)
    padded_image = padded_sample['image']

    norm_image = preprocessing_fn(padded_image)
    tensor_image = to_tensor(norm_image)
    input_tensor = torch.from_numpy(tensor_image).to(DEVICE).unsqueeze(0)

    with torch.no_grad():
        output = model(input_tensor)

    pred_mask = (output > 0.5).float().squeeze(0).cpu().numpy()
    pred_mask = np.argmax(pred_mask, axis=0)
    
    pred_mask_cropped = crop_image(pred_mask)
    pred_colored = colour_code_segmentation(pred_mask_cropped, select_class_rgb_values)

    plt.figure(figsize=(20,8))
    plt.subplot(1, 3, 1)
    plt.title(f"Original Test Image {idx+1}")
    plt.axis('off')
    plt.imshow(image)

    plt.subplot(1, 3, 2)
    plt.title("Ground Truth Mask")
    plt.axis('off')
    plt.imshow(mask)

    plt.subplot(1, 3, 3)
    plt.title("Prediction (Trained 30 Epochs)")
    plt.axis('off')
    plt.imshow(pred_colored)

    plt.savefig(f'outputs/example_{idx+1}.png')
    plt.close()

print("Finished generating 10 examples.")
