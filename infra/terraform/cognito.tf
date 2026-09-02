resource "aws_cognito_user_pool" "this" {
  name = "cognito-auth-chatbot"

  # AC-13: self-service sign-up is disabled at the pool level; every user is
  # pre-provisioned via AdminCreateUser (see scripts/provision-test-user.sh).
  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  username_attributes     = ["email"]
  auto_verified_attributes = ["email"]
}

resource "aws_cognito_user_pool_domain" "this" {
  domain       = var.cognito_domain_prefix
  user_pool_id = aws_cognito_user_pool.this.id
}

# Primary app client -- the only client the React frontend ever uses.
resource "aws_cognito_user_pool_client" "primary" {
  name         = "chatbot-frontend"
  user_pool_id = aws_cognito_user_pool.this.id

  generate_secret = false

  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email"]
  supported_identity_providers         = ["COGNITO"]

  # Exact path, no wildcard -- Cognito rejects wildcard callback URLs.
  # /authorize and /logout both return here; the frontend disambiguates on
  # the query string (see plan.md T7).
  callback_urls = ["http://localhost:5173/callback"]
  logout_urls   = ["http://localhost:5173/callback"]

  prevent_user_existence_errors = "ENABLED"

  # ALLOW_ADMIN_USER_PASSWORD_AUTH is IAM-gated test tooling only (AdminInitiateAuth
  # requires AWS credentials) -- never reachable by an anonymous end user. See
  # plan.md Risks for the bounded-widening rationale.
  explicit_auth_flows = [
    "ALLOW_ADMIN_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
  ]
}

# Second, out-of-audience app client -- used only to mint a wrong-audience
# token for AC-8's negative test. Never used by the frontend, no Hosted UI
# config, not in the API Gateway authorizer's audience list.
resource "aws_cognito_user_pool_client" "test_wrong_audience" {
  name         = "chatbot-test-wrong-audience"
  user_pool_id = aws_cognito_user_pool.this.id

  generate_secret = false

  explicit_auth_flows = [
    "ALLOW_ADMIN_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
  ]
}

# Third, in-audience app client with a 5-minute id_token_validity -- used
# only to mint a token that passes the audience check but is provably
# expired, isolating AC-8's "expired" member from its "wrong audience"
# member. In the API Gateway authorizer's audience list alongside primary.
resource "aws_cognito_user_pool_client" "test_short_ttl" {
  name         = "chatbot-test-short-ttl"
  user_pool_id = aws_cognito_user_pool.this.id

  generate_secret = false

  explicit_auth_flows = [
    "ALLOW_ADMIN_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
  ]

  id_token_validity = 5
  token_validity_units {
    id_token = "minutes"
  }
}
