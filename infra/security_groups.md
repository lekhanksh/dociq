# Security Group Matrix

## `dociq-alb-sg`
- Inbound:
  - `443/tcp` from `0.0.0.0/0`
  - `80/tcp` from `0.0.0.0/0` (redirect only)
- Outbound:
  - `8000/tcp` to `dociq-app-sg`

## `dociq-app-sg` (EC2 in private subnets)
- Inbound:
  - `8000/tcp` from `dociq-alb-sg`
  - Optional `22/tcp` only from bastion/VPN SG
- Outbound:
  - `5432/tcp` to `dociq-db-sg`
  - `443/tcp` to NAT/endpoints for Bedrock, S3, Secrets Manager, KMS, CloudWatch

## `dociq-db-sg` (Aurora)
- Inbound:
  - `5432/tcp` from `dociq-app-sg`
- Outbound:
  - default

## Enforcement Rules
- No direct public ingress to app or DB SG.
- Remove all broad temporary SSH rules after bootstrap.
- Use Session Manager instead of SSH where possible.

## Verification Commands
- Confirm app is not public:
  - `nc -zv <ec2-private-ip> 8000` from outside VPC should fail.
- Confirm DB isolation:
  - `nc -zv <aurora-endpoint> 5432` only works from app host.
