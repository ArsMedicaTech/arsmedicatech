include .env

# To initialize `.venv`: `python3 -m venv .venv`.

run-flask:
	.\.venv\Scripts\activate
	set FLASK_APP=.\app.py
	flask run --host=$(HOST) --port=$(PORT)

# Or, if that doesn't work: python app.py --host=0.0.0.0 --port=3123

# TODO: Doesn't work for some reason. Currently have to run each command manually.
run-flask-linux:
	. .venv/bin/activate
	export FLASK_APP=./app.py
	flask run --host=$(HOST) --port=$(PORT)


run-react-dev:
	API_URL=$(API_URL) npm start


run-react-prod:
	npm install
	API_URL=$(API_URL) npm run build
	npx http-server ./dist -p $(REACT_PORT)


run-mcp:
	.\.venv\Scripts\activate
	python lib/llm/mcp/mcp_server.py


local-encryption-key:
	@echo "Generating encryption key..."
	@python3 -c "import secrets, string; print('ENCRYPTION_KEY=' + ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32)))"



# Docker
auth:
	aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $(DOCKER_REGISTRY)

create-repos:
	aws ecr create-repository --repository-name $(FLASK_IMAGE) --region us-east-1 || true
	aws ecr create-repository --repository-name $(REACT_IMAGE) --region us-east-1 || true
	aws ecr create-repository --repository-name $(MCP_SERVER_IMAGE) --region us-east-1 || true

docker-mcp:
	docker build --build-arg PORT=$(MCP_SERVER_PORT) -t $(DOCKER_REGISTRY)/$(MCP_SERVER_IMAGE):$(MCP_SERVER_VERSION) -f Dockerfile.mcp .
	docker push $(DOCKER_REGISTRY)/$(MCP_SERVER_IMAGE):$(MCP_SERVER_VERSION)
	kubectl rollout restart deployment $(MCP_SERVER_DEPLOYMENT) --namespace=$(NAMESPACE)

docker-flask:
	docker build --build-arg PORT=$(FLASK_PORT) -t $(DOCKER_REGISTRY)/$(FLASK_IMAGE):$(FLASK_VERSION) -f Dockerfile.flask .
	docker push $(DOCKER_REGISTRY)/$(FLASK_IMAGE):$(FLASK_VERSION)
	kubectl rollout restart deployment $(FLASK_DEPLOYMENT) --namespace=$(NAMESPACE)

REACT_BUILD_ARGS=--build-arg PORT=$(REACT_PORT) --build-arg API_URL=$(API_URL) --build-arg SENTRY_DSN=$(SENTRY_DSN)
docker-react:
	docker build $(REACT_BUILD_ARGS) -t $(DOCKER_REGISTRY)/$(REACT_IMAGE):$(REACT_VERSION) -f Dockerfile.react .
	docker push $(DOCKER_REGISTRY)/$(REACT_IMAGE):$(REACT_VERSION)
	kubectl rollout restart deployment $(REACT_DEPLOYMENT) --namespace=$(NAMESPACE)


# Kubernetes and Helm
k8s-init:
	kubectl create namespace $(NAMESPACE)

k8s-auth:
	kubectl create secret docker-registry ecr-secret --docker-server=$(DOCKER_REGISTRY) --docker-username=AWS --docker-password=$(DOCKER_PASSWORD) --namespace=$(NAMESPACE)

k8s-encryption-key:
	@echo "Generating encryption key..."
	@python3 -c "import secrets, string; print('ENCRYPTION_KEY=' + ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32)))"
	kubectl create secret generic encryption-key --from-literal=ENCRYPTION_KEY=your_generated_key_here --namespace=$(NAMESPACE) || true


HF_SECRET=--set huggingface.token=$(HUGGINGFACE_TOKEN)
SURREAL_SECRETS=--set surrealdb.secret.user=$(SURREALDB_USER) --set surrealdb.secret.pass=$(SURREALDB_PASS)
SECRETS=$(SURREAL_SECRETS) $(HF_SECRET) --set migration-openai.apiKey=$(MIGRATION_OPENAI_API_KEY) --set cognito-secret.userPoolClientSecret=$(USER_POOL_CLIENT_SECRET)

k8s-create-secrets:
	kubectl create secret generic surreal-secret --from-literal=user=$(SURREALDB_USER) --from-literal=pass=$(SURREALDB_PASS) --namespace=$(NAMESPACE) || true
	kubectl create secret generic migration-openai-secret --from-literal=apiKey=$(MIGRATION_OPENAI_API_KEY) --namespace=$(NAMESPACE) || true
	kubectl create secret generic cognito-secret --from-literal=userPoolClientSecret=$(USER_POOL_CLIENT_SECRET) --namespace=$(NAMESPACE) || true
	kubectl create secret generic huggingface-token --from-literal=token=$(HUGGINGFACE_TOKEN) --namespace=$(NAMESPACE) || true

k8s-deploy: k8s-create-secrets
	kubectl create namespace $(NAMESPACE) || true
	helm upgrade --install $(NAMESPACE) ./k8s --namespace $(NAMESPACE) $(SECRETS) -f ./k8s/values.yaml

k8s-debug:
	kubectl create namespace $(NAMESPACE) --dry-run=client -o yaml | kubectl apply -f -
	helm template $(NAMESPACE) ./k8s -f ./k8s/values.yaml | kubectl apply --namespace $(NAMESPACE) -f - --dry-run=server


# Tests
test-crud:
	python test_api.py

test-schema:
	python test_schema.py

test-surrealdb:
	python test_db.py

test-create-and-retrieve:
	python test_create_and_retrieve.py

# Playwright E2E Tests
test-e2e:
	npm run test:e2e

test-e2e-ui:
	npm run test:e2e:ui

test-e2e-headed:
	npm run test:e2e:headed

test-e2e-debug:
	npm run test:e2e:debug

test-e2e-report:
	npm run test:e2e:report

test-e2e-install:
	npm run test:e2e:install


# S3

# Create S3 bucket for PDFs...
s3-create:
	aws s3api create-bucket --profile $(AWS_PROFILE) --region $(AWS_REGION) --bucket $(S3_BUCKET) | true
	aws s3api put-public-access-block --profile $(AWS_PROFILE) --region $(AWS_REGION) --bucket $(S3_BUCKET) --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true | true
	aws s3api put-bucket-policy --profile $(AWS_PROFILE) --region $(AWS_REGION) --bucket $(S3_BUCKET) --policy file://config/s3_iam_bucket_policy.json | true


s3-iam:
	aws iam create-user --profile $(AWS_PROFILE) --region $(AWS_REGION) --user-name flask-s3-writer | true
	aws iam put-user-policy --profile $(AWS_PROFILE) --region $(AWS_REGION) --user-name flask-s3-writer --policy-name FlaskS3WritePolicy --policy-document file://config/flask_s3_write_policy.json | true
	aws iam create-access-key --user-name flask-s3-writer

textract-iam:
	aws iam create-user --profile $(AWS_PROFILE) --region $(AWS_REGION) --user-name flask-textract-user | true
	aws iam put-user-policy --profile $(AWS_PROFILE) --region $(AWS_REGION) --user-name flask-textract-user --policy-name TextractReadPolicy --policy-document file://config/textract_read_write_policy.json | true
	aws iam create-access-key --user-name flask-textract-user


# Celery
CELERY_IMAGE=celery-worker
CELERY_VERSION=1.0.0


celery-docker:
	docker build -t $(CELERY_IMAGE):$(CELERY_VERSION) -f Dockerfile.celery .

celery-run:
	docker run -d --name celery-worker -e CELERY_BROKER_URL=redis://$(REDIS_HOST):$(REDIS_PORT)/1 -e SENTRY_DSN=$(SENTRY_DSN) -e CELERY_RESULT_BACKEND=redis://$(REDIS_HOST):$(REDIS_PORT)/1 $(CELERY_IMAGE):$(CELERY_VERSION)



# Microservices

# LiveKit
ENV_VARS=LIVEKIT_API_KEY=$(LIVEKIT_API_KEY) LIVEKIT_API_SECRET=$(LIVEKIT_API_SECRET) LIVEKIT_S3_ACCESS_KEY=$(LIVEKIT_S3_ACCESS_KEY) LIVEKIT_S3_SECRET_KEY=$(LIVEKIT_S3_SECRET_KEY) LIVEKIT_S3_REGION=$(LIVEKIT_S3_REGION) LIVEKIT_S3_BUCKET=$(LIVEKIT_S3_BUCKET)

livekit-local:
	@echo "Starting LiveKit server locally..."
	$(ENV_VARS) envsubst < micro/livekit/egress.template.yaml > micro/livekit/egress.yaml
	$(ENV_VARS) envsubst < micro/livekit/livekit.template.yaml > micro/livekit/livekit.yaml
	cd micro/livekit && PWD=$$(pwd) docker compose build egress
	cd micro/livekit && PWD=$$(pwd) docker compose build api
	cd micro/livekit && PWD=$$(pwd) docker compose --env-file .env up -d

# Create S3 bucket for LiveKit recordings...
livekit-s3-iam:
	aws iam create-user --profile $(AWS_PROFILE) --region $(AWS_REGION) --user-name livekit-s3-writer | true
	aws iam put-user-policy --profile $(AWS_PROFILE) --region $(AWS_REGION) --user-name livekit-s3-writer --policy-name LiveKitS3WritePolicy --policy-document file://config/livekit_s3_write_policy.json | true
	aws iam create-access-key --user-name livekit-s3-writer

livekit-s3-create:
	aws s3api create-bucket --profile $(AWS_PROFILE) --region $(AWS_REGION) --bucket $(LIVEKIT_S3_BUCKET) | true
	aws s3api put-public-access-block --profile $(AWS_PROFILE) --region $(AWS_REGION) --bucket $(LIVEKIT_S3_BUCKET) --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true | true
	aws s3api put-bucket-policy --profile $(AWS_PROFILE) --region $(AWS_REGION) --bucket $(LIVEKIT_S3_BUCKET) --policy file://config/livekit_s3_bucket_policy.json | true


livekit-docker-create:
	aws ecr create-repository --repository-name $(LIVEKIT_API_IMAGE) --region us-east-1 || true
	aws ecr create-repository --repository-name $(LIVEKIT_EGRESS_IMAGE) --region us-east-1 || true

livekit-docker:
	docker build --build-arg LIVEKIT_API_KEY=$(LIVEKIT_API_KEY) --build-arg LIVEKIT_API_SECRET=$(LIVEKIT_API_SECRET) --build-arg LIVEKIT_S3_ACCESS_KEY=$(LIVEKIT_S3_ACCESS_KEY) --build-arg LIVEKIT_S3_SECRET_KEY=$(LIVEKIT_S3_SECRET_KEY) --build-arg LIVEKIT_S3_REGION=$(LIVEKIT_S3_REGION) --build-arg LIVEKIT_S3_BUCKET=$(LIVEKIT_S3_BUCKET) -t $(DOCKER_REGISTRY)/$(LIVEKIT_API_IMAGE):$(LIVEKIT_API_VERSION) -f micro/livekit/Dockerfile.api ./micro/livekit
	docker push $(DOCKER_REGISTRY)/$(LIVEKIT_API_IMAGE):$(LIVEKIT_API_VERSION)
	kubectl rollout restart deployment $(LIVEKIT_API_DEPLOYMENT) --namespace=$(NAMESPACE)

livekit-egress-docker:
	docker build -t $(DOCKER_REGISTRY)/$(LIVEKIT_EGRESS_IMAGE):$(LIVEKIT_EGRESS_VERSION) -f micro/livekit/Dockerfile.egress ./micro/livekit
	docker push $(DOCKER_REGISTRY)/$(LIVEKIT_EGRESS_IMAGE):$(LIVEKIT_EGRESS_VERSION)
	kubectl rollout restart deployment $(LIVEKIT_EGRESS_DEPLOYMENT) --namespace=$(NAMESPACE)

livekit-egress-debug:
	kubectl delete pod debug-egress -n arsmedicatech --ignore-not-found
	kubectl patch serviceaccount default -n arsmedicatech -p '{"imagePullSecrets":[{"name":"ecr-secret"}]}'
	kubectl run debug-egress -n arsmedicatech --rm -it --image=$(DOCKER_REGISTRY)/$(LIVEKIT_EGRESS_IMAGE):$(LIVEKIT_EGRESS_VERSION) --restart=Never --command -- sleep 3600

livekit-egress-debug-access:
	kubectl exec -it -n arsmedicatech debug-egress -- sh



# NER
ner-docker-create:
	aws ecr create-repository --repository-name $(NER_API_IMAGE) --region us-east-1 || true

ner-docker:
	docker build -t $(DOCKER_REGISTRY)/$(NER_API_IMAGE):$(NER_API_VERSION) -f micro/ner/Dockerfile ./micro/ner
	docker push $(DOCKER_REGISTRY)/$(NER_API_IMAGE):$(NER_API_VERSION)
	kubectl rollout restart deployment $(NER_API_DEPLOYMENT) --namespace=$(NAMESPACE)

ner-run:
	docker run -d -p 8000:8000 --name extractor $(DOCKER_REGISTRY)/$(NER_API_IMAGE):$(NER_API_VERSION)


NER_URL=http://localhost:8000/
NER_URL=https://demo.arsmedicatech.com/ner/
ner-test:
	curl -X POST $(NER_URL)extract -H "Content-Type: application/json" -d '{"text":"Patient presents with Type 2 diabetes mellitus and essential hypertension."}'



# Reasoning Engine (Haskell)
# Docker commands are in respective repository

# Create S3 bucket for Ontologies...
ontologies-s3-iam:
	aws iam create-user --profile $(AWS_PROFILE) --region $(AWS_REGION) --user-name ontologies-s3-read-write | true
	aws iam put-user-policy --profile $(AWS_PROFILE) --region $(AWS_REGION) --user-name ontologies-s3-read-write --policy-name OntologiesS3ReadWritePolicy --policy-document file://config/ontologies_s3_read_write_policy.json | true
	aws iam create-access-key --user-name ontologies-s3-read-write

ontologies-s3-create:
	aws s3api create-bucket --profile $(AWS_PROFILE) --region $(AWS_REGION) --bucket $(ONTOLOGIES_S3_BUCKET) | true
	aws s3api put-public-access-block --profile $(AWS_PROFILE) --region $(AWS_REGION) --bucket $(ONTOLOGIES_S3_BUCKET) --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true | true
	aws s3api put-bucket-policy --profile $(AWS_PROFILE) --region $(AWS_REGION) --bucket $(ONTOLOGIES_S3_BUCKET) --policy file://config/ontologies_s3_bucket_policy.json | true


# MedGemma
medgemma-docker-create:
	aws ecr create-repository --repository-name $(MEDGEMMA_IMAGE) --region us-east-1 || true

medgemma-docker:
	docker build -t $(DOCKER_REGISTRY)/$(MEDGEMMA_IMAGE):$(MEDGEMMA_VERSION) -f Dockerfile.medgemma .
	docker push $(DOCKER_REGISTRY)/$(MEDGEMMA_IMAGE):$(MEDGEMMA_VERSION)
	kubectl rollout restart deployment $(MEDGEMMA_DEPLOYMENT) --namespace=$(NAMESPACE)


runpod:
	kubectl create ns kube-system || true
	kubectl create secret generic runpod-api-secret -n kube-system --from-literal=RUNPOD_API_KEY=$(RUNPOD_API_KEY)
	helm install runpod-kubelet oci://ghcr.io/bsvogler/helm/runpod-kubelet --namespace kube-system --set runpod.existingSecret=runpod-api-secret --set runpod.maxGpuPrice=$(MAX_GPU_PRICE)



# Google Cloud credentials

# First, run `gcloud auth login` to authenticate via browser.

# Had to do some of the initial configuration for the project and consent screen manually on the GCP console.
# See README.

.PHONY: gcloud-init
gcloud-init:
	gcloud config set project $(GCP_PROJECT_ID)
	gcloud services enable iap.googleapis.com
	gcloud auth application-default set-quota-project $(GCP_PROJECT_ID)
	gcloud alpha iap oauth-brands create --application_title="$(APP_NAME)" --support_email="$(SUPPORT_EMAIL)"
	gcloud services enable iam.googleapis.com
	gcloud services enable cloudresourcemanager.googleapis.com
	gcloud services enable oauth2.googleapis.com

.PHONY: gcloud-client
gcloud-client:
	gcloud alpha iam oauth-clients create --display_name="$(APP_NAME)" --redirect_uris="$(CALLBACK_URL)"

.PHONY: gcloud-credentials
gcloud-credentials:
	gcloud alpha iam oauth-clients list



# Makefile for AWS Cognito deployment on Windows
# Requires: AWS CLI, Make for Windows (GnuWin32, or via Git Bash, or WSL)

# Output file
CONFIG_FILE = config.py

# Default target
.PHONY: deploy-cognito
deploy-cognito: deploy-cognito-stack get-cognito-outputs create-cognito-config

# Deploy CloudFormation stack
.PHONY: deploy-cognito-stack
deploy-cognito-stack:
	@echo "Deploying CloudFormation stack..."
	aws cloudformation deploy \
		--template-file $(TEMPLATE_FILE) \
		--stack-name $(STACK_NAME) \
		--parameter-overrides \
			AppName=$(APP_NAME) \
			GoogleClientId=$(GOOGLE_CLIENT_ID) \
			GoogleClientSecret=$(GOOGLE_CLIENT_SECRET) \
			CallbackURL=$(CALLBACK_URL) \
		--capabilities CAPABILITY_IAM \
		--region $(AWS_REGION) \
		--profile $(AWS_PROFILE)

# Get stack outputs
.PHONY: get-cognito-outputs
get-cognito-outputs:
	@echo "Getting CloudFormation stack outputs..."
	$(eval USER_POOL_ID := $(shell aws cloudformation describe-stacks --stack-name $(STACK_NAME) --query "Stacks[0].Outputs[?ExportName=='$(STACK_NAME)-UserPoolId'].OutputValue" --output text --region $(AWS_REGION) --profile $(AWS_PROFILE)))
	$(eval USER_POOL_CLIENT_ID := $(shell aws cloudformation describe-stacks --stack-name $(STACK_NAME) --query "Stacks[0].Outputs[?ExportName=='$(STACK_NAME)-UserPoolClientId'].OutputValue" --output text --region $(AWS_REGION) --profile $(AWS_PROFILE)))
	$(eval COGNITO_DOMAIN := $(shell aws cloudformation describe-stacks --stack-name $(STACK_NAME) --query "Stacks[0].Outputs[?ExportName=='$(STACK_NAME)-CognitoDomain'].OutputValue" --output text --region $(AWS_REGION) --profile $(AWS_PROFILE)))

	@echo "Getting User Pool Client Secret..."
	$(eval USER_POOL_CLIENT_SECRET := $(shell aws cognito-idp describe-user-pool-client --user-pool-id $(USER_POOL_ID) --client-id $(USER_POOL_CLIENT_ID) --query "UserPoolClient.ClientSecret" --output text --region $(AWS_REGION) --profile $(AWS_PROFILE)))

	@echo "----------------------------------------"
	@echo "Cognito Configuration:"
	@echo "----------------------------------------"
	@echo "USER_POOL_ID=$(USER_POOL_ID)"
	@echo "USER_POOL_CLIENT_ID=$(USER_POOL_CLIENT_ID)"
	@echo "USER_POOL_CLIENT_SECRET=$(USER_POOL_CLIENT_SECRET)"
	@echo "COGNITO_DOMAIN=$(COGNITO_DOMAIN)"
	@echo "----------------------------------------"

# Create configuration file
.PHONY: create-cognito-config
create-cognito-config:
	@echo "Generating config file for Flask app..."
	@echo "# AWS Cognito Configuration" > $(CONFIG_FILE)
	@echo "AWS_REGION = '$(AWS_REGION)'" >> $(CONFIG_FILE)
	@echo "COGNITO_DOMAIN = '$(COGNITO_DOMAIN)'" >> $(CONFIG_FILE)
	@echo "USER_POOL_ID = '$(USER_POOL_ID)'" >> $(CONFIG_FILE)
	@echo "CLIENT_ID = '$(USER_POOL_CLIENT_ID)'" >> $(CONFIG_FILE)
	@echo "CLIENT_SECRET = '$(USER_POOL_CLIENT_SECRET)'" >> $(CONFIG_FILE)
	@echo "REDIRECT_URI = '$(CALLBACK_URL)'" >> $(CONFIG_FILE)
	@echo "Configuration file ($(CONFIG_FILE)) created successfully!"

# Delete the CloudFormation stack
.PHONY: clean-cognito
clean-cognito:
	@echo "Deleting CloudFormation stack..."
	aws cloudformation delete-stack --stack-name $(STACK_NAME) --region $(AWS_REGION) --profile $(AWS_PROFILE)
	@echo "Waiting for stack deletion to complete..."
	aws cloudformation wait stack-delete-complete --stack-name $(STACK_NAME) --region $(AWS_REGION) --profile $(AWS_PROFILE)
	@echo "Stack deleted successfully!"
	@if exist $(CONFIG_FILE) del $(CONFIG_FILE)

# Show help
.PHONY: cognito-help
cognito-help:
	@echo "Available targets:"
	@echo "  deploy        - Deploy stack and create config file"
	@echo "  deploy-stack  - Deploy the CloudFormation stack"
	@echo "  get-outputs   - Get and display stack outputs"
	@echo "  create-config - Create Flask config file"
	@echo "  clean         - Delete the CloudFormation stack"
	@echo "  help          - Show this help message"
	@echo ""
	@echo "Before running, edit the Makefile to set your:"
	@echo "- AWS region"
	@echo "- Google OAuth credentials"
	@echo "- App name and callback URL"
