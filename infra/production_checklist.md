# Production Go-Live Checklist

## Security
- [ ] ALB has WAF attached with managed + rate-limit rules.
- [ ] App and DB subnets are private; no public IP on EC2/Aurora.
- [ ] S3 bucket enforces TLS and SSE-KMS.
- [ ] IAM role is least-privilege and no static AWS keys are used.
- [ ] Secrets come only from Secrets Manager/SSM.
- [ ] CORS restricted to production frontend domain.

## Reliability
- [ ] Aurora backups + PITR enabled.
- [ ] S3 versioning and lifecycle policies enabled.
- [ ] Rolling or blue/green deployment strategy tested.
- [ ] Health checks and rollback procedure documented.

## Observability
- [ ] App logs and ALB logs in CloudWatch/S3.
- [ ] Audit log shipping enabled.
- [ ] Alerts configured for 5xx, latency, CPU/memory, and DB errors.

## Validation
- [ ] Upload document flow validated in production-like environment.
- [ ] RAG query relevance validated with sample company docs.
- [ ] Auth, RBAC, and document isolation tested for each role.
- [ ] Load test baseline completed and accepted.
