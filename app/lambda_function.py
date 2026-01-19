import json
from pathlib import Path
import pickle
import os

from pydantic import ValidationError

import boto3
import pandas as pd
import xgboost as xgb

from .schemas import DiamondInput


BUCKET_NAME = os.environ.get("MODELS_BUCKET", "ml-artifacts")
MODEL_KEY = os.environ.get("MODEL_KEY", "model.json")
PREPROCESSOR_KEY = os.environ.get("PREPROCESSOR_KEY", "preprocessor.pkl")

LOCAL_MODEL_PATH = f"/tmp/{MODEL_KEY}"
LOCAL_PREPROCESSOR_PATH = f"/tmp/{PREPROCESSOR_KEY}"

S3_ENDPOINT = os.environ.get("AWS_ENDPOINT_URL")

s3 = boto3.client("s3", endpoint_url=S3_ENDPOINT)

PREPROCESSOR = None
MODEL = None


def load_from_s3():
    global PREPROCESSOR, MODEL
    if not (Path(LOCAL_MODEL_PATH).exists() and Path(LOCAL_PREPROCESSOR_PATH).exists()):
        s3.download_file(BUCKET_NAME, MODEL_KEY, LOCAL_MODEL_PATH)
        s3.download_file(BUCKET_NAME, PREPROCESSOR_KEY, LOCAL_PREPROCESSOR_PATH)

    with open(LOCAL_PREPROCESSOR_PATH, "rb") as f:
        PREPROCESSOR = pickle.load(f)

    MODEL = xgb.XGBRegressor()
    MODEL.load_model(LOCAL_MODEL_PATH)


try:
    load_from_s3()
except Exception as e:
    print(f"Initial load failed: {e}")


def handler(event, context):
    global PREPROCESSOR, MODEL

    if PREPROCESSOR is None or MODEL is None:
        try:
            load_from_s3()
        except Exception as e:
            return {
                "statusCode": 500,
                "body": json.dumps(
                    {"error": "Failed to load models", "detail": str(e)}
                ),
            }

    try:
        body = json.loads(event.get("body", "{}"))
        data = DiamondInput(**body)
        input_dict = data.model_dump()

        dv = PREPROCESSOR["vectorizer"]
        feature_names = PREPROCESSOR["features"]

        X_encoded = dv.transform([input_dict])

        X_input = pd.DataFrame(X_encoded, columns=dv.get_feature_names_out())
        X_input = X_input.reindex(columns=feature_names, fill_value=0)

        predicted_price = float(MODEL.predict(X_input)[0])

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "predicted_price": round(predicted_price, 2),
                }
            ),
        }

    except ValidationError as ve:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Validation Error", "details": ve.errors()}),
        }
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
