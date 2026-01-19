## 💎 Diamonds 💎

## Top level overview

### What is it

Using ML for predicting price of a diamond.

### Dataset

[Diamonds](https://www.kaggle.com/datasets/shivam2503/diamonds) dataset contains the prices and other attributes of almost 54,000 diamonds.

Dataset is available on [Kaggle](https://www.kaggle.com/datasets/shivam2503/diamonds).
Same dataset is builtin into `Seaborn` library.

See [instructions](#load-dataset) for details.

### EDA

Full info about exploring dataset and model training provided in [`notebook.ipynb`](notebook.ipynb#EDA).

### Models

We will compare multiple different models:
* Linear model ([Ridge](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html))
* [Random Forest Regressor](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html)
* [XGBoost](https://xgboost.readthedocs.io/en/latest/index.html)

Using hyper-parameters tuning, we compare top performer of each version, and best model will be selected for production.

See [Model Training](notebook.ipynb#Model-Training) section in notebook for more info.

After testing, the best mobel was `xgboost`, providing R2-score `0.9801`.


### Script

Model training routine is exported into script.

Script for training can be found in `scripts/train.py`

### Serving model

Out target is to create infra to simulate serving model via AWS-lambda.

But there is 2 way of going live. One is [simple](#test-without-cluster), with just docker and another is hard. 

Important notice: this is the most challenging part of the project. For details see [instructions below](#serving)


## Instructions

Important notice: all instructions are verified for linux-based system

While there is a change of successfully running without any changes on `MacOS` and `WSL`, there is no any guarantee of it.

### Load dataset

Dataset is available via `Seaborn` - and we take this. Basically, to get data you just have to execute notebook or script, and data will be loaded.

While you can manually load data from [Kaggle](https://www.kaggle.com/datasets/shivam2503/diamonds) nor notebook, nor script currently does not support it.

### Dependency management

Project uses [`uv`](https://docs.astral.sh/uv/) as dependency manager.

List of used libs is provided in `pyproject.toml`.

Some deps are marked as `dev`. Such dependencies are needed only for executing training script and/or notebook.

To install all dependencies:

```bash
uv sync
```

To install only main deps

```bash
uv sync --no-dev
```

### Serving

No AWS account is needed - we use `kind` to run a Kubernetes cluster locally and [`LocalStack`](https://www.localstack.cloud/) to provide the AWS services (S3 and Lambda).

Pretrained model and preprocessor can be found in `models/` folder.

A lot of tooling and extra steps ahead, brace yourself.

#### Tools

I repeat, this was tested on linux-based os. Adjust accordantly.

Here is a list of tools needed for this steps:

* docker
* curl
* [kind](https://kind.sigs.k8s.io/docs/user/quick-start/)
* [kubectl](https://kubernetes.io/docs/tasks/tools/)
* [Helm](https://helm.sh/)
* [AWS CLI](https://aws.amazon.com/cli/)
* [aws-sam-cli-local](https://github.com/localstack/aws-sam-cli-local)

#### Test without cluster

You could use just docker image to validate, that project is working.

1. Build docker image. This image can be tested manually without any extra infra and later loaded into cluster.

```bash
docker build -t ml-zoomcap-capstone .
```

2. Run docker image serving our model:
```bash
docker run -it -p 9000:8080 \
  -v $(pwd)/models/model.json:/tmp/model.json \
  -v $(pwd)/models/preprocessor.pkl:/tmp/preprocessor.pkl \
  -e MODELS_BUCKET=dummy \
  -e AWS_ACCESS_KEY_ID=testing \
  -e AWS_SECRET_ACCESS_KEY=testing \
  ml-zoomcap-capstone
```

We start server, and mount trained model into image. At this step we don't have S3-instance to load models from there. `MODELS_BUCKET` is also related to this functionality.

`AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are part on AWS infra. As we will use local emulator it is not really important.

Port is mapped to `9000`.

3. In another terminal execute next command to send data into lambda-function

```bash
curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d '{ "body": "{\"depth\": 62.1, \"table\": 58.0, \"x\": 5.1, \"y\": 5.1, \"z\": 3.2, \"cut\": \"Premium\", \"color\": \"E\", \"clarity\": \"SI1\"}"}'
```

If every thing work - your response will be like this `{"statusCode": 200, "body": "{\"predicted_price\": 417.78}"}`


#### Infrastructure Setup

1. Create the Cluster

```bash
kind create cluster --name mlzoomcamp-capstone
```

2. Install `LocalStack` into cluster.

```bash
helm repo add localstack https://localstack.github.io/helm-charts
helm install localstack localstack/localstack \
  --namespace localstack --create-namespace \
  --set service.type=NodePort
```

3. Verifying

```bash
kubectl get pods -n localstack
```

4. Port forwarding

In another terminal execute to forward port from cluster, so we can use s3

```bash
kubectl port-forward svc/localstack -n localstack 4566:4566
```

#### S3

1. Using AWS CLI set up some important env variables

```bash
aws configure set aws_access_key_id test
aws configure set aws_secret_access_key test
aws configure set region us-east-1
```

2. Create bucket

```bash
aws --endpoint-url=http://localhost:4566 s3 mb s3://ml-artifacts
```

3. Upload trained model and preprocessor into bucket

```bash
aws --endpoint-url=http://localhost:4566 s3 cp models/model.json s3://ml-artifacts/
aws --endpoint-url=http://localhost:4566 s3 cp models/preprocessor.pkl s3://ml-artifacts/

```

#### Serverless

Last step before running! At this step we have to adjust `infra/template.yaml` by hand.



0.  Getting actual address of S3.
```bash
export NODE_PORT=$(kubectl get --namespace "localstack" -o jsonpath="{.spec.ports[0].nodePort}" services localstack)
export NODE_IP=$(kubectl get nodes --namespace "localstack" -o jsonpath="{.items[0].status.addresses[0].address}")
echo http://$NODE_IP:$NODE_PORT
```

Replace `AWS_ENDPOINT_URL` in `infra/template.yaml` with result before going to next step.

1. Building 
```bash
uvx --from aws-sam-cli-local samlocal build -t infra/template.yaml
```

2. Serving
```bash
uvx --from aws-sam-cli-local samlocal local start-api --docker-network kind
```


#### Testing

Execute 

```bash
curl -X POST http://127.0.0.1:3000/predict\
  -H "Content-Type: application/json" \
  -d '{
        "depth": 62.1,
        "table": 58.0,
        "x": 4.34,
        "y": 4.39,
        "z": 2.71,
        "cut": "Premium",
        "color": "G",
        "clarity": "VS1"
      }'
```

Result should be like this: `{"predicted_price": 519.84}`

If you got it - congratulations! 