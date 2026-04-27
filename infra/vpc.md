# Private VPC Blueprint (Staging + Prod)

## Goal
Run DocIQ backend and Aurora pgvector in private subnets. Only ALB is internet-facing.

## Network Layout
- VPC CIDR: `10.20.0.0/16`
- Public subnets (2 AZs): ALB + NAT gateways
- Private app subnets (2 AZs): EC2 Docker hosts
- Private data subnets (2 AZs): Aurora PostgreSQL
- Route policy:
  - Public subnets -> Internet Gateway
  - Private app subnets -> NAT Gateway
  - Private data subnets -> no direct internet route

## Recommended AWS Endpoints
Create VPC interface/gateway endpoints to reduce internet egress and tighten controls:
- `com.amazonaws.<region>.s3` (gateway endpoint)
- `com.amazonaws.<region>.secretsmanager`
- `com.amazonaws.<region>.logs`
- `com.amazonaws.<region>.kms`
- `com.amazonaws.<region>.bedrock-runtime`

## Staging vs Production
- Staging: single EC2 app host in private app subnet, one NAT gateway.
- Production: at least 2 EC2 app hosts across AZs and one NAT gateway per AZ.

## DNS and Ingress
- Route53 `staging-api.your-domain.com` -> staging ALB
- Route53 `api.your-domain.com` -> production ALB
- ACM certificates in-region for both hostnames.

## Validation Checklist
- ALB has public IPs; EC2 and Aurora do not.
- EC2 has outbound internet only through NAT/endpoints.
- Aurora accessible only from app security group.
- No `0.0.0.0/0` ingress on EC2 or Aurora.
