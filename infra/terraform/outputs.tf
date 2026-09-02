output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.this.id
}

output "cognito_hosted_ui_domain" {
  value = "${aws_cognito_user_pool_domain.this.domain}.auth.us-east-2.amazoncognito.com"
}

output "cognito_primary_client_id" {
  value = aws_cognito_user_pool_client.primary.id
}

output "cognito_test_wrong_audience_client_id" {
  value = aws_cognito_user_pool_client.test_wrong_audience.id
}

output "cognito_test_short_ttl_client_id" {
  value = aws_cognito_user_pool_client.test_short_ttl.id
}

output "api_invoke_url" {
  value = aws_apigatewayv2_stage.prod.invoke_url
}

output "lambda_function_name" {
  value = aws_lambda_function.chat.function_name
}

output "log_group_name" {
  value = aws_cloudwatch_log_group.lambda.name
}
