import os, cv2
import numpy as np
import pandas as pd
import torch
import albumentations as album
import segmentation_models_pytorch as smp
import matplotlib.pyplot as plt
from torch.utils.data import DataLoader

def one_hot_encode(label, label_values):
    semantic_map = []
    for colour in label_values:
        equality = np.equal(label, colour)
        class_map = np.all(equality, axis = -1)
        semantic_map.append(class_map)
    semantic_map = np.stack(semantic_map, axis=-1)
    return semantic_map

class BuildingsDataset(torch.utils.data.Dataset):
    def __init__(self, images_dir, masks_dir, class_rgb_values=None, augmentation=None, preprocessing=None):
        self.image_paths = [os.path.join(images_dir, image_id) for image_id in sorted(os.listdir(images_dir))]
        self.mask_paths = [os.path.join(masks_dir, image_id) for image_id in sorted(os.listdir(masks_dir))]
        self.class_rgb_values = class_rgb_values
        self.augmentation = augmentation
        self.preprocessing = preprocessing
    
    def __getitem__(self, i):
        image = cv2.cvtColor(cv2.imread(self.image_paths[i]), cv2.COLOR_BGR2RGB)
        mask = cv2.cvtColor(cv2.imread(self.mask_paths[i]), cv2.COLOR_BGR2RGB)
        mask = one_hot_encode(mask, self.class_rgb_values).astype('float')
        
        if self.augmentation:
            sample = self.augmentation(image=image, mask=mask)
            image, mask = sample['image'], sample['mask']
        if self.preprocessing:
            sample = self.preprocessing(image=image, mask=mask)
            image, mask = sample['image'], sample['mask']
            
        return image, mask
        
    def __len__(self):
        return len(self.image_paths)

def get_training_augmentation():
    train_transform = [    
        album.RandomCrop(height=256, width=256),
        album.OneOf([
                album.HorizontalFlip(p=1),
                album.VerticalFlip(p=1),
                album.RandomRotate90(p=1),
            ], p=0.75,
        ),
    ]
    return album.Compose(train_transform)

def get_validation_augmentation():   
    test_transform = [
        album.PadIfNeeded(min_height=1536, min_width=1536, border_mode=0),
    ]
    return album.Compose(test_transform)

def to_tensor(x, **kwargs):
    return x.transpose(2, 0, 1).astype('float32')

def get_preprocessing(preprocessing_fn=None):
    _transform = []
    if preprocessing_fn:
        _transform.append(album.Lambda(image=preprocessing_fn))
    _transform.append(album.Lambda(image=to_tensor, mask=to_tensor))
    return album.Compose(_transform)

class DiceLoss(torch.nn.Module):
    def forward(self, pr, gt, eps=1e-7):
        pr = pr.view(pr.size(0), -1)
        gt = gt.view(gt.size(0), -1)
        intersection = torch.sum(pr * gt, dim=1)
        union = torch.sum(pr, dim=1) + torch.sum(gt, dim=1)
        return torch.mean(1.0 - (2. * intersection + eps) / (union + eps))

def calculate_iou(preds, targets, threshold=0.5):
    preds = (preds > threshold).float()
    intersection = (preds * targets).sum((1, 2, 3))
    union = (preds + targets).sum((1, 2, 3)) - intersection
    return (intersection / (union + 1e-7)).mean().item()

def main():
    DATA_DIR = os.path.join('notebooks', 'input', 'massachusetts-roads-dataset', 'tiff')
    x_train_dir = os.path.join(DATA_DIR, 'train')
    y_train_dir = os.path.join(DATA_DIR, 'train_labels')
    x_valid_dir = os.path.join(DATA_DIR, 'val')
    y_valid_dir = os.path.join(DATA_DIR, 'val_labels')

    class_names = ['background', 'road']
    class_rgb_values = [[0, 0, 0], [255, 255, 255]]
    select_class_rgb_values = np.array(class_rgb_values)

    ENCODER = 'efficientnet-b7'
    ENCODER_WEIGHTS = 'imagenet'
    CLASSES = class_names
    ACTIVATION = 'sigmoid'

    print("Initializing model...")
    model = smp.Unet(
        encoder_name=ENCODER, 
        encoder_weights=ENCODER_WEIGHTS, 
        classes=len(CLASSES), 
        activation=ACTIVATION,
    )

    preprocessing_fn = smp.encoders.get_preprocessing_fn(ENCODER, ENCODER_WEIGHTS)

    train_dataset = BuildingsDataset(
        x_train_dir, y_train_dir, 
        augmentation=get_training_augmentation(),
        preprocessing=get_preprocessing(preprocessing_fn),
        class_rgb_values=select_class_rgb_values,
    )

    valid_dataset = BuildingsDataset(
        x_valid_dir, y_valid_dir, 
        augmentation=get_validation_augmentation(), 
        preprocessing=get_preprocessing(preprocessing_fn),
        class_rgb_values=select_class_rgb_values,
    )

    # Note: num_workers=0 on Windows to avoid Multiprocessing issues easily.
    train_loader = DataLoader(train_dataset, batch_size=8, shuffle=True, num_workers=0)
    valid_loader = DataLoader(valid_dataset, batch_size=1, shuffle=False, num_workers=0)

    EPOCHS = 5
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on device: {DEVICE}")
    model = model.to(DEVICE)

    criterion = DiceLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.0001)
    lr_scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
        optimizer, T_0=1, T_mult=2, eta_min=5e-5,
    )

    best_iou_score = 0.0
    train_logs_list, valid_logs_list = [], []

    print("Starting training loop...")
    for epoch in range(EPOCHS):
        print(f'\nEpoch: {epoch}')
        
        # Training
        model.train()
        train_loss = 0.0
        train_iou = 0.0
        for i, (images, masks) in enumerate(train_loader):
            images, masks = images.to(DEVICE), masks.to(DEVICE)
            
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, masks)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            train_iou += calculate_iou(outputs, masks)
            
        train_loss /= len(train_loader)
        train_iou /= len(train_loader)
        
        # Validation
        model.eval()
        valid_loss = 0.0
        valid_iou = 0.0
        with torch.no_grad():
            for images, masks in valid_loader:
                images, masks = images.to(DEVICE), masks.to(DEVICE)
                outputs = model(images)
                loss = criterion(outputs, masks)
                
                valid_loss += loss.item()
                valid_iou += calculate_iou(outputs, masks)
                
        valid_loss /= len(valid_loader)
        valid_iou /= len(valid_loader)
        
        print(f"Train Loss: {train_loss:.4f} | Train IoU: {train_iou:.4f}")
        print(f"Valid Loss: {valid_loss:.4f} | Valid IoU: {valid_iou:.4f}")
        
        train_logs_list.append({'dice_loss': train_loss, 'iou_score': train_iou})
        valid_logs_list.append({'dice_loss': valid_loss, 'iou_score': valid_iou})
        
        lr_scheduler.step()

        if best_iou_score < valid_iou:
            best_iou_score = valid_iou
            torch.save(model, 'weights/road_model_5_epochs.pth')
            print('Model saved!')

    print("Training complete! Generating plots...")
    
    train_logs_df = pd.DataFrame(train_logs_list)
    valid_logs_df = pd.DataFrame(valid_logs_list)

    plt.figure(figsize=(20,8))
    plt.plot(train_logs_df.index.tolist(), train_logs_df.iou_score.tolist(), lw=3, label = 'Train')
    plt.plot(valid_logs_df.index.tolist(), valid_logs_df.iou_score.tolist(), lw=3, label = 'Valid')
    plt.xlabel('Epochs', fontsize=20)
    plt.ylabel('IoU Score', fontsize=20)
    plt.title('IoU Score Plot', fontsize=20)
    plt.legend(loc='best', fontsize=16)
    plt.grid()
    plt.savefig('outputs/road_iou_score_plot_5ep.png')
    plt.close()

    plt.figure(figsize=(20,8))
    plt.plot(train_logs_df.index.tolist(), train_logs_df.dice_loss.tolist(), lw=3, label = 'Train')
    plt.plot(valid_logs_df.index.tolist(), valid_logs_df.dice_loss.tolist(), lw=3, label = 'Valid')
    plt.xlabel('Epochs', fontsize=20)
    plt.ylabel('Dice Loss', fontsize=20)
    plt.title('Dice Loss Plot', fontsize=20)
    plt.legend(loc='best', fontsize=16)
    plt.grid()
    plt.savefig('outputs/road_dice_loss_plot_5ep.png')
    plt.close()
    
    print("Done!")

if __name__ == '__main__':
    main()
