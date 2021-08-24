# -*- coding: utf-8 -*-
"""Framework_add_batchnorm.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/15qxijudN_s1b3fXaozM9AM1eVaUUGUje
"""

import torch
import torchvision
import numpy as np
import matplotlib.pyplot as plt
import torch.nn as nn
import torch.nn.functional as F
from torchvision.datasets import CIFAR10
from torchvision.transforms import ToTensor
from torchvision.utils import make_grid
from torch.utils.data.dataloader import DataLoader
from torch.utils.data import random_split

"""## Exploring the CIFAR10 dataset"""

dataset = CIFAR10(root='data/', download=True, transform=ToTensor())
test_dataset = CIFAR10(root='data/', train=False, transform=ToTensor())

print("dataset size: " + str(len(dataset)))
print("testing dataset size: " + str(len(test_dataset)))
print("Number of classes: " + str(len(dataset.classes)))
print(dataset.classes)

#check the torch size
# img, label = dataset[0]
# img_shape = img.shape

#check the images belonging to each class
print("Number of images in each class: ")
class_count = {}
for _, index in dataset:
    label = dataset.classes[index]
    if label not in class_count:
        class_count[label] = 0
    class_count[label] += 1
class_count

"""## Preparing the data for training

We'll use a validation set with 5000 images (10% of the dataset). To ensure we get the same validation set each time, we'll set PyTorch's random number generator to a seed value of 43.
"""

#set the taining and validation size (9:1)
torch.manual_seed(43)
val_size = 5000
train_size = len(dataset) - val_size

#training, validation dataset spliting
train_ds, val_ds = random_split(dataset, [train_size, val_size])
print("training dataset size" + str(len(train_ds)) + ", " + "validation dataset size" + str(len(val_ds)))

"""We can now create data loaders to load the data in batches."""

#batch Size
batch_size=128

#create data loader to load the data in batches
train_loader = DataLoader(train_ds, batch_size, shuffle=True, num_workers=0, pin_memory=True)
val_loader = DataLoader(val_ds, batch_size*2, num_workers=0, pin_memory=True)
test_loader = DataLoader(test_dataset, batch_size*2, num_workers=0, pin_memory=True)

"""Let's visualize a batch of data using the `make_grid` helper function from Torchvision."""

for images, _ in train_loader:
    print('images.shape:', images.shape)
    plt.figure(figsize=(16,8))
    plt.axis('off')
    plt.imshow(make_grid(images, nrow=16).permute((1, 2, 0)))
    break

"""## Base Model class & Training on GPU

Let's create a base model class, which contains everything except the model architecture
i.e. it wil not contain the `__init__` and `__forward__` methods.
We will later extend this class to try out different architectures. In fact, you can extend this model to solve any image classification problem.
"""

def accuracy(outputs, labels):
    _, preds = torch.max(outputs, dim=1)
    return torch.tensor(torch.sum(preds == labels).item() / len(preds))

class ImageClassificationBase(nn.Module):
    def training_step(self, batch):
        images, labels = batch
        out = self(images)                  # Generate predictions
        loss = F.cross_entropy(out, labels) # Calculate loss
        return loss

    def validation_step(self, batch):
        images, labels = batch
        out = self(images)                    # Generate predictions
        loss = F.cross_entropy(out, labels)   # Calculate loss
        acc = accuracy(out, labels)           # Calculate accuracy
        return {'val_loss': loss.detach(), 'val_acc': acc}

    def validation_epoch_end(self, outputs):
        batch_losses = [x['val_loss'] for x in outputs]
        epoch_loss = torch.stack(batch_losses).mean()   # Combine losses
        batch_accs = [x['val_acc'] for x in outputs]
        epoch_acc = torch.stack(batch_accs).mean()      # Combine accuracies
        return {'val_loss': epoch_loss.item(), 'val_acc': epoch_acc.item()}

    def epoch_end(self, epoch, result):
        print("Epoch [{}], val_loss: {:.4f}, val_acc: {:.4f}".format(epoch, result['val_loss'], result['val_acc']))

def evaluate(model, val_loader):
    outputs = [model.validation_step(batch) for batch in val_loader]
    return model.validation_epoch_end(outputs)

def fit(epochs, lr, model, train_loader, val_loader, opt_func=torch.optim.SGD):
    history = []
    optimizer = opt_func(model.parameters(), lr)
    for epoch in range(epochs):
        # Training Phase
        for batch in train_loader:
            loss = model.training_step(batch)
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()
        # Validation phase
        result = evaluate(model, val_loader)
        model.epoch_end(epoch, result)
        history.append(result)
    return history

def count_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)

def get_default_device():
    """Pick GPU if available, else CPU"""
    # if torch.cuda.is_available():
    #     return torch.device('cuda')
    # else:
    return torch.device('cpu')

def to_device(data, device):
    """Move tensor(s) to chosen device"""
    if isinstance(data, (list,tuple)):
        return [to_device(x, device) for x in data]
    return data.to(device, non_blocking=True)

class DeviceDataLoader():
    """Wrap a dataloader to move data to a device"""
    def __init__(self, dl, device):
        self.dl = dl
        self.device = device

    def __iter__(self):
        """Yield a batch of data after moving it to device"""
        for b in self.dl:
            yield to_device(b, self.device)

    def __len__(self):
        """Number of batches"""
        return len(self.dl)

"""Let us also define a couple of helper functions for plotting the losses & accuracies."""

def plot_losses(history):
    losses = [x['val_loss'] for x in history]
    plt.plot(losses, '-x')
    plt.xlabel('epoch')
    plt.ylabel('loss')
    plt.title('Loss vs. No. of epochs');

def plot_accuracies(history):
    accuracies = [x['val_acc'] for x in history]
    plt.plot(accuracies, '-x')
    plt.xlabel('epoch')
    plt.ylabel('accuracy')
    plt.title('Accuracy vs. No. of epochs');

"""Let's move our data loaders to the appropriate device."""

train_loader = DeviceDataLoader(train_loader, device)
val_loader = DeviceDataLoader(val_loader, device)
test_loader = DeviceDataLoader(test_loader, device)

"""## Training the model

We will make several attempts at training the model. Each time, try a different architecture and a different set of learning rates. Here are some ideas to try:
- Increase or decrease the number of hidden layers
- Increase of decrease the size of each hidden layer
- Try different activation functions
- Try training for different number of epochs
- Try different learning rates in every epoch

What's the highest validation accuracy you can get to? **Can you get to 50% accuracy? What about 60%?**
"""

input_size = 3*32*32
output_size = 10

"""
**Q: Extend the `ImageClassificationBase` class to complete the model definition.**

Hint: Define the `__init__` and `forward` methods."""

class CIFAR10Model(ImageClassificationBase):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 9, 3, padding=1)
        self.conv2 = nn.Conv2d(9, 9, 3, padding=1)
        self.maxpool1 = nn.MaxPool2d(2, 2)
        self.conv3 = nn.Conv2d(9, 18, 3, padding=1)
        self.conv4 = nn.Conv2d(18, 18, 3, padding=1)
        self.conv5 = nn.Conv2d(18, 36, 3, padding=1)
        self.conv6 = nn.Conv2d(36, 36, 3, padding=1)

        self.linear1 = nn.Linear(576, 100)
        self.linear2 = nn.Linear(100, output_size)

        self.dropout1 = nn.Dropout2d(0.5)

        self.bn1 = nn.BatchNorm2d(num_features = 9)
        self.bn2 = nn.BatchNorm2d(num_features = 18)
        self.bn3 = nn.BatchNorm2d(num_features = 36)

    def forward(self, xb):
        # Apply layers & activation functions
        out = xb
        #part 1
        out = self.conv1(out)
        out = F.relu(out)
        out = self.bn1(out)
        out = self.conv2(out)
        out = F.relu(out)
        out = self.bn1(out)
        out = self.maxpool1(out)

        #part 2
        out = self.conv3(out)
        out = F.relu(out)
        out = self.bn2(out)
        out = self.conv4(out)
        out = F.relu(out)
        out = self.bn2(out)
        out = self.maxpool1(out)

        #part 3
        out = self.conv5(out)
        out = F.relu(out)
        out = self.bn3(out)
        out = self.conv6(out)
        out = F.relu(out)
        out = self.bn3(out)
        out = self.maxpool1(out)

        #part 4
        out = torch.flatten(out,1)
        out = self.linear1(out)
        out = F.relu(out)
        out = self.dropout1(out)
        out = self.linear2(out)

        return out

"""You can now instantiate the model, and move it the appropriate device."""

model = to_device(CIFAR10Model(), device)

count_parameters(model)

"""Before you train the model, it's a good idea to check the validation loss & accuracy with the initial set of weights."""

history = [evaluate(model, val_loader)]
history

"""**Q: Train the model using the `fit` function to reduce the validation loss & improve accuracy.**

Leverage the interactive nature of Jupyter to train the model in multiple phases, adjusting the no. of epochs & learning rate each time based on the result of the previous training phase.
"""

history += fit(10, 1e-1, model, train_loader, val_loader)

history += fit(10, 1e-2, model, train_loader, val_loader)

history += fit(10, 1e-3, model, train_loader, val_loader)

history += fit(10, 1e-4, model, train_loader, val_loader)

"""Plot the losses and the accuracies to check if you're starting to hit the limits of how well your model can perform on this dataset. You can train some more if you can see the scope for further improvement."""

plot_losses(history)

plot_accuracies(history)

"""Finally, evaluate the model on the test dataset report its final performance."""

evaluate(model, test_loader)

final_result = evaluate(model, test_loader)
test_acc = final_result['val_acc']
test_loss = final_result['val_loss']
print(final_result)