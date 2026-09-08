import os
import cv2
import numpy as np
import torch
import albumentations as album
import segmentation_models_pytorch as smp
import matplotlib.pyplot as plt

def colour_code_segmentation(image, label_values):
    colour_codes = np.array(label_values)
    x = colour_codes[image.astype(int)]
    return x

# Get class values
class_names = ['background', 'road']
class_rgb_values = [[0, 0, 0], [255, 255, 255]]
select_class_rgb_values = np.array(class_rgb_values)

DATA_DIR = os.path.join('notebooks', 'input', 'massachusetts-roads-dataset', 'tiff')
x_test_dir = os.path.join(DATA_DIR, 'test')
y_test_dir = os.path.join(DATA_DIR, 'test_labels')

# Get image paths
image_paths = [os.path.join(x_test_dir, image_id) for image_id in sorted(os.listdir(x_test_dir))]
mask_paths = [os.path.join(y_test_dir, image_id) for image_id in sorted(os.listdir(y_test_dir))]

# Read first test image (index 0)
idx = 1
image = cv2.cvtColor(cv2.imread(image_paths[idx]), cv2.COLOR_BGR2RGB)
mask = cv2.cvtColor(cv2.imread(mask_paths[idx]), cv2.COLOR_BGR2RGB)

print("Loading trained model...")
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = torch.load('weights/best_road_model.pth', map_location=DEVICE, weights_only=False)
model.eval()

# Pad image to 1536x1536 (multiple of 32 for UNet)
test_transform = album.Compose([
    album.PadIfNeeded(min_height=1536, min_width=1536, border_mode=0),
])

def to_tensor(x, **kwargs):
    return x.transpose(2, 0, 1).astype('float32')

preprocessing_fn = smp.encoders.get_preprocessing_fn('efficientnet-b7', 'imagenet')

padded_sample = test_transform(image=image)
padded_image = padded_sample['image']

# Preprocess and to tensor
norm_image = preprocessing_fn(padded_image)
tensor_image = to_tensor(norm_image)
input_tensor = torch.from_numpy(tensor_image).to(DEVICE).unsqueeze(0)

print("Running inference...")
with torch.no_grad():
    output = model(input_tensor)

# Process output
pred_mask = (output > 0.5).float().squeeze(0).cpu().numpy() # (2, 1536, 1536)
pred_mask = np.argmax(pred_mask, axis=0) # (1536, 1536)

# Crop back to 1500x1500
def crop_image(img, target_size=1500):
    padding = (img.shape[0] - target_size) // 2
    if padding == 0:
        return img
    return img[padding:-padding, padding:-padding]

pred_mask_cropped = crop_image(pred_mask)
pred_colored = colour_code_segmentation(pred_mask_cropped, select_class_rgb_values)

plt.figure(figsize=(20,8))
plt.subplot(1, 3, 1)
plt.title("Original Test Image")
plt.axis('off')
plt.imshow(image)

plt.subplot(1, 3, 2)
plt.title("Ground Truth Mask")
plt.axis('off')
plt.imshow(mask)

plt.subplot(1, 3, 3)
plt.title("Prediction Road (Trained 30 Epochs)")
plt.axis('off')
plt.imshow(pred_colored)

plt.savefig('outputs/trained_demo_road_output.png')
print("Saved outputs/trained_demo_road_output.png")
