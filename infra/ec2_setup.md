# EC2 (Private Subnet) Deployment

## Required Pattern
- EC2 app hosts run in private app subnets.
- No public IP on app hosts.
- Access for ops via SSM Session Manager (preferred) or bastion.

## IAM Instance Profile
Attach a least-privilege policy that grants:
- S3 read/write only for your document bucket prefixes
- Bedrock `InvokeModel` only for allowed model ARNs
- KMS `Encrypt/Decrypt/GenerateDataKey` for DocIQ CMK
- Secrets Manager read only for `/dociq/<env>/` secrets
- CloudWatch Logs write

## Bootstrap
```bash
sudo yum update -y
sudo yum install -y docker
sudo systemctl enable docker --now
sudo usermod -aG docker ec2-user
```

## Deploy with Docker Compose
```bash
cd /opt/dociq
# copy backend/.env.staging (or prod) from SSM/Secrets Manager generated values
docker compose -f docker-compose.staging.yml pull
docker compose -f docker-compose.staging.yml up -d --build
```

## Hardening
- IMDSv2 required.
- Root volume encrypted with KMS.
- SSM agent enabled, SSH disabled if possible.
- Auto patching via SSM Patch Manager.
- CloudWatch agent forwards app + audit logs.
