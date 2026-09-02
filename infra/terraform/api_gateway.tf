resource "aws_apigatewayv2_api" "this" {
  name          = "cognito-auth-chatbot"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins     = ["http://localhost:5173"]
    allow_methods     = ["POST", "OPTIONS"]
    allow_headers     = ["authorization", "content-type"]
    allow_credentials = false
  }
}

# JWT authorizer's audience deliberately includes only the primary and the
# short-TTL test client -- NOT the wrong-audience test client, which exists
# specifically to fail this check (AC-8).
resource "aws_apigatewayv2_authorizer" "cognito" {
  api_id           = aws_apigatewayv2_api.this.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name             = "cognito-jwt"

  jwt_configuration {
    audience = [
      aws_cognito_user_pool_client.primary.id,
      aws_cognito_user_pool_client.test_short_ttl.id,
    ]
    issuer = "https://${aws_cognito_user_pool.this.endpoint}"
  }
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.this.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.chat.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "chat" {
  api_id    = aws_apigatewayv2_api.this.id
  route_key = "POST /chat"

  target             = "integrations/${aws_apigatewayv2_integration.lambda.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_stage" "prod" {
  api_id      = aws_apigatewayv2_api.this.id
  name        = "prod"
  auto_deploy = true
}

# Least-privilege: scoped to exactly this API's POST /chat route, so no
# other API Gateway (in this or any other account) can invoke the function
# through this permission (AC-18).
resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.chat.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.this.execution_arn}/*/POST/chat"
}
