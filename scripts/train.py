import pickle

from argparse import ArgumentParser

import seaborn as sns
import xgboost as xgb

from sklearn.feature_extraction import DictVectorizer
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split


MODEL_FILE = "model.json"
PREPROCESSOR_FILE = "preprocessor.pkl"
STORAGE_PATH = "./models/"


def train() -> tuple[xgb.XGBModel, DictVectorizer]:
    print("Loading data ...")
    df = sns.load_dataset("diamonds", True)
    y = df["price"]
    X = df[["carat", "cut", "color", "clarity", "depth", "table"]]

    X_train_full, X_test, y_train_full, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    dv = DictVectorizer(sparse=False)
    X_train_enc = dv.fit_transform(X_train_full.to_dict(orient="records"))
    X_test_enc = dv.transform(X_test.to_dict(orient="records"))

    print("Training started ...")
    final_model = xgb.XGBRegressor(
        objective="reg:squarederror",
        random_state=42,
        subsample=0.9,
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        colsample_bytree=0.8,
    )

    final_model = final_model.fit(X_train_enc, y_train_full)
    y_test_predicted = final_model.predict(X_test_enc)
    print("Training finished ...")
    print(f"Test R2 Score: {r2_score(y_test, y_test_predicted):.4f}")

    return final_model, dv


def save_model(model, preprocessor):
    print(f"Saved artefacts to '{STORAGE_PATH}'")
    model.save_model(f"{STORAGE_PATH}{MODEL_FILE}")
    with open(f"{STORAGE_PATH}{PREPROCESSOR_FILE}", "wb") as f:
        pickle.dump(
            {
                "vectorizer": preprocessor,
                "features": list(list(preprocessor.get_feature_names_out())),
            },
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )


if __name__ == "__main__":
    parser = ArgumentParser(description="train CLI")
    parser.add_argument("-n", "--no-save", action="store_true")

    model, preprocessor = train()

    call_args = vars(parser.parse_args())
    if call_args["no_save"]:
        exit(0)

    save_model(model, preprocessor)
