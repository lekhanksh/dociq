# ALB + WAF Setup

## Listener Strategy
- `80` -> redirect `301` to `443`
- `443` -> target group `dociq-app-tg` on `8000`
- TLS policy: modern only (e.g. `ELBSecurityPolicy-TLS13-1-2-2021-06`)

## Target Group
- Health endpoint: `/health`
- Deregistration delay: 30s
- Stickiness: disabled

## WAF
Attach AWS WAF web ACL to ALB:
- AWS managed common rule set
- SQLi + XSS managed rules
- IP reputation rule set
- Rate-based rule (for abusive IPs)

## Access Logs
- Enable ALB access logs to encrypted S3 bucket.
- Retain at least 90 days in staging, 365 days in production.

## Validation
```bash
curl -I http://api.your-domain.com
curl https://api.your-domain.com/health
```
