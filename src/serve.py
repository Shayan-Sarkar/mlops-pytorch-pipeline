import io
import os
from contextlib import asynccontextmanager

import torch
import torch.nn.functional as F
from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image
from torchvision import transforms

from model import get_model

CHECKPOINT_PATH = os.environ.get("CHECKPOINT_PATH", "/app/checkpoints/classifier_v1.pt")
MODEL_ARCHITECTURE = os.environ.get("MODEL_ARCHITECTURE", "resnet18")
NUM_CLASSES = int(os.environ.get("NUM_CLASSES", "10"))

CIFAR10_CLASSES = [
    "airplane", "automobile", "bird", "cat", "deer",
    "dog", "frog", "horse", "ship", "truck",
]

CIFAR10_MEAN = [0.4914, 0.4822, 0.4465]
CIFAR10_STD = [0.2470, 0.2435, 0.2616]

preprocess = transforms.Compose([
    transforms.Resize((32, 32)),
    transforms.ToTensor(),
    transforms.Normalize(mean=CIFAR10_MEAN, std=CIFAR10_STD),
])

state = {"model": None}


def load_model():
    architecture = MODEL_ARCHITECTURE
    num_classes = NUM_CLASSES
    if os.path.exists(CHECKPOINT_PATH):
        checkpoint = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=True)
        architecture = checkpoint.get("architecture", architecture)
        num_classes = checkpoint.get("num_classes", num_classes)
        model = get_model(architecture=architecture, num_classes=num_classes)
        model.load_state_dict(checkpoint["model_state_dict"])
        model.eval()
        return model
    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    state["model"] = load_model()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    if state["model"] is None:
        raise HTTPException(status_code=503, detail="model not loaded")
    return {"status": "ok"}


@app.post("/predict")
async def predict(image: UploadFile = File(...)):
    if state["model"] is None:
        raise HTTPException(status_code=503, detail="model not loaded")

    contents = await image.read()
    try:
        img = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="invalid image")

    tensor = preprocess(img).unsqueeze(0)
    with torch.no_grad():
        logits = state["model"](tensor)
        probabilities = F.softmax(logits, dim=1).squeeze(0).tolist()

    return {
        "predictions": [
            {"class": CIFAR10_CLASSES[i], "probability": round(p, 6)}
            for i, p in enumerate(probabilities)
        ]
    }
