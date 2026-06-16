from ultralytics import YOLO
from dotenv import load_dotenv
from PIL import Image,ImageDraw
import requests
import io
import numpy as np
import torch
torch.set_num_threads(1)
from torchvision import transforms
import vit_animesion
from vit_animesion.configs import PRETRAINED_CONFIGS, ViTConfigExtended
import pandas as pd
import os
import urllib.request
#load keys
load_dotenv()

characterDetector  = 'weights/jjk_classifier.ckpt'
classnamesCSV = 'weights/classid_classname.csv'

#for gpu for character detection
device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

def load_jjk_classifier():
    #ml jumbo idk how to configure
    config = ViTConfigExtended(**PRETRAINED_CONFIGS['B_16']['config'])
    config.num_classes = 21
    m = vit_animesion.ViT(config, name='B_16', pretrained=False)

    m.load_state_dict(torch.load(characterDetector, map_location='cpu'))
    m.eval()
    return m.to(device)

faceDetector = YOLO('weights/jjk_facedetector.pt')
model = load_jjk_classifier()

df = pd.read_csv(classnamesCSV, header=None, names=['class_id', 'class_name'])
idToCharacter = dict(zip(df['class_id'], df['class_name']))

def processImage(slanderImageURL,profilePicURL,character):
    """
    detects heads of images, and creates agenda, and sends it as bytes to discordBot.py
    """
    boundingBoxList = detectHead(slanderImageURL)
    finalImageBytes = placeHead(slanderImageURL,profilePicURL,boundingBoxList,character)
    return finalImageBytes

def detectHead(imageURL) -> list:
    """
    detects all the heads
    """
    response = requests.get(imageURL).content
    image = Image.open(io.BytesIO(response)).convert("RGB")
    imageArray = np.array(image)    
    results = faceDetector(imageArray,conf=0.05, iou=0)
    res = []
    for result in results:
        boxes = result.boxes
        for box in boxes:   
            res.append(box.xyxy[0].tolist())
    return res




def placeHead(slanderImageURL,profilePicURL,boundingBoxList,characterName):
    """
    places the head on the image
    """
    baseImageBytes = requests.get(slanderImageURL).content
    overlayImageBytes = requests.get(profilePicURL).content
    
    baseImage = Image.open(io.BytesIO(baseImageBytes)).convert("RGBA")
    overlayImage = Image.open(io.BytesIO(overlayImageBytes)).convert("RGBA")

    for x_min,y_min,x_max,y_max in boundingBoxList:
        boxWidth = int(x_max - x_min)
        boxHeight = int(y_max - y_min)
        #get cropped image to check if we actually want to overlay on this character
        face_crop = baseImage.crop((int(x_min), int(y_min), int(x_max), int(y_max))).convert("RGB")
        #preprcess face_crop for model
        transform = transforms.Compose([
                transforms.Resize((224,224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[.5,.5,.5],std=[.5,.5,.5])
        ])
        #apply transformations for image to be recognized
        transformedCrop = transform(face_crop).unsqueeze(0).to(device)
        # run model
        with torch.no_grad():   
            predicitions = model(transformedCrop)           
            predictedCharID = predicitions.argmax(dim=1).item()  
            predictedCharName = idToCharacter[predictedCharID]
            print(f'Expected: {characterName} | Got: {predictedCharName}')
            #if there is only one face, just put the profle pic on there. if there is more, we need to skip one of them 
            if len(boundingBoxList) > 1 and predictedCharName != characterName:
                continue

        #resize, circle frame    on a copy
        currentOverlayImage = overlayImage.copy().resize((boxWidth, boxHeight))
        
        
        overlayMask = Image.new("L",currentOverlayImage.size,0)
        ImageDraw.Draw(overlayMask).ellipse((0,0,boxWidth,boxHeight),fill=255,)
        currentOverlayImage.putalpha(overlayMask)

        #put circle framed + resized profile picture on base image 
        baseImage.paste(currentOverlayImage,(int(x_min),int(y_min)),mask=currentOverlayImage)
    output = io.BytesIO()
    baseImage.convert("RGB").save(output, format="JPEG")
    result_bytes = output.getvalue()

    return result_bytes
