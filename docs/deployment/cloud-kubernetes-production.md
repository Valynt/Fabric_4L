# Cloud Kubernetes Production Setup for www.valuepact.ai

This guide covers deploying Value Fabric to a cloud Kubernetes cluster (GKE/EKS/AKS) for production on www.valuepact.ai.

## Choose Your Cloud Provider

- **GKE (Google Cloud)** - Recommended for ease of use
- **EKS (AWS)** - Good if you already use AWS
- **AKS (Azure)** - Good if you already use Azure

## Option A: Google Kubernetes Engine (GKE)

### Prerequisites

```bash
# Install gcloud CLI
curl https://sdk.cloud.google.com | bash

# Initialize gcloud
gcloud init

# Install kubectl
gcloud components install kubectl
```

### Create GKE Cluster

```bash
# Set your project ID
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Create cluster (adjust region and node specs as needed)
gcloud container clusters create valuepact-prod \
  --region=us-central1 \
  --machine-type=e2-standard-4 \
  --num-nodes=2 \
  --node-locations=us-central1-a,us-central1-b \
  --enable-autoscaling \
  --min-nodes=2 \
  --max-nodes=6 \
  --enable-ip-alias \
  --create-subnetwork="" \
  --network-tier=PREMIUM \
  --enable-private-nodes \
  --enable-master-authorized-networks \
  --master-authorized-networks=<YOUR_IP>/32 \
  --enable-autoupgrade \
  --enable-autorepair \
  --cluster-version=1.34.1-gke.1500000

# Get cluster credentials
gcloud container clusters get-credentials valuepact-prod --region=us-central1

# Verify cluster
kubectl get nodes
```

### Install NGINX Ingress Controller

```bash
# Add Helm repository
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

# Install NGINX Ingress Controller
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-port"=80 \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-protocol"=HTTP \
  --set controller.service.loadBalancerIP=<STATIC_IP_IF_NEEDED>

# Wait for LoadBalancer IP
kubectl get svc -n ingress-nginx
```

### Install cert-manager

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.16.1/cert-manager.crds.yaml

helm repo add jetstack https://charts.jetstack.io
helm repo update

helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.16.1 \
  --set installCRDs=true

# Create ClusterIssuer
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: security@valuepact.ai
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

## Option B: Amazon EKS (AWS)

### Prerequisites

```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Install eksctl
curl --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin

# Configure AWS credentials
aws configure
```

### Create EKS Cluster

```bash
# Create cluster
eksctl create cluster \
  --name valuepact-prod \
  --region us-east-1 \
  --version 1.34 \
  --node-type t3.medium \
  --nodes 2 \
  --nodes-min 2 \
  --nodes-max 6 \
  --managed \
  --with-oidc \
  --ssh-access \
  --ssh-public-key=<YOUR_SSH_KEY>

# Get cluster credentials
aws eks update-kubeconfig --name valuepact-prod --region us-east-1

# Verify cluster
kubectl get nodes
```

### Install AWS Load Balancer Controller

```bash
# Create IAM policy
curl -o iam_policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/main/docs/install/iam_policy.json

aws iam create-policy \
  --policy-name AWSLoadBalancerControllerIAMPolicy \
  --policy-document file://iam_policy.json

# Create IAM role and service account
eksctl create iamserviceaccount \
  --cluster=valuepact-prod \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --attach-policy-arn=arn:aws:iam::<AWS_ACCOUNT_ID>:policy/AWSLoadBalancerControllerIAMPolicy \
  --approve \
  --override-existing-serviceaccounts

# Install AWS Load Balancer Controller
helm repo add eks https://aws.github.io/eks-charts
helm repo update

helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=valuepact-prod \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller

# Install NGINX Ingress Controller
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace
```

### Install cert-manager

```bash
# Same as GKE option above
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.16.1/cert-manager.crds.yaml

helm repo add jetstack https://charts.jetstack.io
helm repo update

helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.16.1 \
  --set installCRDs=true

# Create ClusterIssuer (same as GKE)
```

## Option C: Azure Kubernetes Service (AKS)

### Prerequisites

```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login to Azure
az login

# Install kubectl
az aks install-cli
```

### Create AKS Cluster

```bash
# Create resource group
az group create --name valuepact-rg --location eastus

# Create cluster
az aks create \
  --resource-group valuepact-rg \
  --name valuepact-prod \
  --node-count 2 \
  --node-vm-size Standard_DS4_v2 \
  --enable-cluster-autoscaler \
  --min-count 2 \
  --max-count 6 \
  --kubernetes-version 1.34.1 \
  --enable-managed-identity \
  --network-plugin azure \
  --load-balancer-sku standard \
  --enable-private-cluster

# Get cluster credentials
az aks get-credentials --resource-group valuepact-rg --name valuepact-prod

# Verify cluster
kubectl get nodes
```

### Install NGINX Ingress Controller

```bash
# Install NGINX Ingress Controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-port"=80

# Get LoadBalancer IP
kubectl get svc -n ingress-nginx
```

### Install cert-manager

```bash
# Same as GKE option above
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.16.1/cert-manager.crds.yaml

helm repo add jetstack https://charts.jetstack.io
helm repo update

helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.16.1 \
  --set installCRDs=true

# Create ClusterIssuer (same as GKE)
```

## Deploy Value Fabric to Cloud Cluster

### Step 1: Create Namespace

```bash
kubectl create namespace value-fabric
```

### Step 2: Apply Base Configuration

```bash
kubectl apply -k k8s/base
```

### Step 3: Apply Production Ingress Configuration

```bash
kubectl apply -k k8s/deployments/prod-nginx
```

### Step 4: Get LoadBalancer IP

```bash
kubectl get svc -n ingress-nginx ingress-nginx-controller
```

Note the EXTERNAL-IP address.

### Step 5: Configure DNS at Spaceship.com

Log into Spaceship.com and configure DNS records:

```
Type: A Record
Name: www
Value: <LOADBALANCER_IP>
TTL: 300

Type: A Record
Name: accounts
Value: <LOADBALANCER_IP>
TTL: 300
```

### Step 6: Verify Certificate Issuance

```bash
# Check certificate status
kubectl get certificate -n value-fabric

# Check certificate request
kubectl get certificaterequest -n value-fabric

# Describe certificate if issues
kubectl describe certificate frontend-tls -n value-fabric
```

### Step 7: Verify Deployment

```bash
# Check all pods
kubectl get pods -n value-fabric

# Check ingress
kubectl get ingress -n value-fabric

# Test HTTPS access
curl -I https://www.valuepact.ai
python scripts/ci/production_edge_smoke.py --base-url https://www.valuepact.ai
```

## Update Infisical Secrets

Update the following Infisical secrets for production:

**Path: /shared/auth**

```
CLERK_ISSUER=https://accounts.valuepact.ai
CLERK_JWT_AUDIENCE=fabric4l-api
CLERK_AUTHORIZED_PARTIES=https://www.valuepact.ai
CLERK_JWKS_URL=https://accounts.valuepact.ai/.well-known/jwks.json
```

**Path: /api-gateway**

```
CLERK_SECRET_KEY=<your-clerk-secret-key>
CLERK_WEBHOOK_SECRET=<your-clerk-webhook-secret>
FABRIC_AUTH_SIGNING_KEY=<ed25519-private-pem>
FABRIC_AUTH_SIGNING_KID=gateway-k1
FABRIC_AUTH_PUBLIC_KEYS=<json-public-key-set>
```

**Path: /apps/web**

```
VITE_CLERK_PUBLISHABLE_KEY=<your-clerk-publishable-key>
VITE_AUTH_PROVIDER=clerk
```

## Update Clerk Configuration

In your Clerk Dashboard:

**Allowed Origins:**

- https://www.valuepact.ai

**Redirect URLs:**

- After sign-in: https://www.valuepact.ai/workspaces
- After sign-up: https://www.valuepact.ai/onboarding

**Webhook Endpoint:**

- The application edge does not expose `/internal/webhooks/clerk`. Provision a
  separately reviewed same-host webhook route with signature verification and
  dedicated rate limits before enabling Clerk webhooks.

## Production Checklist

- [ ] Cloud cluster created (GKE/EKS/AKS)
- [ ] NGINX Ingress Controller installed
- [ ] cert-manager installed
- [ ] ClusterIssuer configured
- [ ] Value Fabric deployed
- [ ] LoadBalancer IP obtained
- [ ] DNS records configured at Spaceship.com
- [ ] SSL certificates issued
- [ ] HTTPS accessible at https://www.valuepact.ai
- [ ] API returns JSON at https://www.valuepact.ai/api/v1/auth/health
- [ ] Clerk authentication configured
- [ ] Infisical secrets updated
- [ ] Health checks passing

## Cost Estimates (Monthly)

**GKE (Google Cloud):**

- 2x e2-standard-4 nodes: ~$200
- LoadBalancer: ~$20
- Storage: ~$50-100
- **Total: ~$270-320/month**

**EKS (AWS):**

- 2x t3.medium nodes: ~$100
- EKS control plane: ~$73
- LoadBalancer: ~$20
- Storage: ~$50-100
- **Total: ~$243-293/month**

**AKS (Azure):**

- 2x Standard_DS4_v2 nodes: ~$280
- LoadBalancer: ~$20
- Storage: ~$50-100
- **Total: ~$350-400/month**

## Scaling Considerations

For production, consider:

- Enable cluster autoscaler (configured above)
- Set up horizontal pod autoscalers (already in k8s/base/hpa/)
- Configure pod disruption budgets (already in k8s/base/pdb/)
- Set up monitoring and alerting
- Configure backup strategies

## Security Hardening

- Enable private clusters where possible
- Use network policies (already configured in k8s/base/network-policies/)
- Enable pod security standards
- Configure audit logging
- Enable secrets encryption
- Regular security updates

## Troubleshooting

### Certificate not issuing

```bash
# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager

# Check ingress annotations
kubectl describe ingress -n value-fabric
```

### LoadBalancer not getting IP

```bash
# Check ingress controller
kubectl get svc -n ingress-nginx

# Check cloud provider console for LoadBalancer status
```

### Pods not starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n value-fabric

# Check logs
kubectl logs <pod-name> -n value-fabric
```

## Monitoring Setup

Install monitoring stack:

```bash
# Install Prometheus and Grafana
kubectl apply -k k8s/base

# Access Grafana
kubectl port-forward -n value-fabric svc/grafana 3000:3000
```

## Backup Strategy

Configure regular backups:

```bash
# PostgreSQL backups (already configured as CronJob)
kubectl get cronjob -n value-fabric postgres-backup

# Neo4j backups (already configured as CronJob)
kubectl get cronjob -n value-fabric neo4j-backup
```
