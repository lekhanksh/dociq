# ─────────────────────────────────────────────
# Secrets Manager (Req 1.2)
# ─────────────────────────────────────────────
resource "aws_secretsmanager_secret" "app" {
  name                    = "${local.name}/app-secrets"
  recovery_window_in_days = 7
  tags                    = local.tags
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    jwt_secret = var.jwt_secret
  })
}
