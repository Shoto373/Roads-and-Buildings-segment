import os
import cv2
import numpy as np
import pandas as pd
import torch
import segmentation_models_pytorch as smp
import matplotlib.pyplot as plt

# Define dataset paths
DATA_DIR = os.path.join('notebooks', 'input', 'massachusetts-buildings-dataset', 'tiff')
x_train_dir = os.path.join(DATA_DIR, 'train')
y_train_dir = os.path.join(DATA_DIR, 'train_labels')

# Get class values
select_classes = ['background', 'building']
class_names = ['background', 'building']
class_rgb_values = [[0, 0, 0], [255, 255, 255]]
select_class_indices = [class_names.index(cls.lower()) for cls in select_classes]
select_class_rgb_values =  np.array(class_rgb_values)[select_class_indices]

def visualize(save_path, **images):
    n_images = len(images)
    plt.figure(figsize=(20,8))
    for idx, (name, image) in enumerate(images.items()):
        plt.subplot(1, n_images, idx + 1)
        plt.xticks([]); plt.yticks([])
        plt.title(name.replace('_',' ').title(), fontsize=20)
        plt.imshow(image)
    plt.savefig(save_path)
    plt.close()

def one_hot_encode(label, label_values):
    semantic_map = []
    for colour in label_values:
        equality = np.equal(label, colour)
        class_map = np.all(equality, axis = -1)
        semantic_map.append(class_map)
    semantic_map = np.stack(semantic_map, axis=-1)
    return semantic_map

def reverse_one_hot(image):
    return np.argmax(image, axis = -1)

def colour_code_segmentation(image, label_values):
    colour_codes = np.array(label_values)
    x = colour_codes[image.astype(int)]
    return x

class BuildingsDataset(torch.utils.data.Dataset):
    def __init__(self, images_dir, masks_dir, class_rgb_values=None):
        self.image_paths = [os.path.join(images_dir, image_id) for image_id in sorted(os.listdir(images_dir))]
        self.mask_paths = [os.path.join(masks_dir, image_id) for image_id in sorted(os.listdir(masks_dir))]
        self.class_rgb_values = class_rgb_values
    
    def __getitem__(self, i):
        image = cv2.cvtColor(cv2.imread(self.image_paths[i]), cv2.COLOR_BGR2RGB)
        mask = cv2.cvtColor(cv2.imread(self.mask_paths[i]), cv2.COLOR_BGR2RGB)
        mask = one_hot_encode(mask, self.class_rgb_values).astype('float')
        return image, mask
        
    def __len__(self):
        return len(self.image_paths)

# Load dataset and get one image
dataset = BuildingsDataset(x_train_dir, y_train_dir, class_rgb_values=select_class_rgb_values)
image, mask = dataset[0]

# Initialize model
print("Initializing model...")
model = smp.Unet(
    encoder_name="efficientnet-b7",
    encoder_weights="imagenet",
    in_channels=3,
    classes=1,
)

# Run inference
print("Running inference...")
# Model expects input of shape (B, C, H, W) and normalized values usually, but let's just do a basic forward pass
# to show it outputs the correct shape and can run without error. 
# image shape from cv2 is (H, W, C), so we transpose to (C, H, W)
input_tensor = torch.from_numpy(image).float().permute(2, 0, 1).unsqueeze(0)

with torch.no_grad():
    output = model(input_tensor)
    
# output shape is (1, 1, H, W)
pred_mask = output.squeeze(0).squeeze(0).numpy()
# threshold for visualization
pred_mask = (pred_mask > 0).astype(np.uint8)
# color code it so it's visible (black/white)
pred_colored = np.stack([pred_mask*255]*3, axis=-1)

# Visualize original, ground truth, and untrained prediction
visualize(
    'outputs/demo_output.png',
    original_image = image,
    ground_truth_mask = colour_code_segmentation(reverse_one_hot(mask), select_class_rgb_values),
    untrained_model_prediction = pred_colored
)
print("Output saved to outputs/demo_output.png")
