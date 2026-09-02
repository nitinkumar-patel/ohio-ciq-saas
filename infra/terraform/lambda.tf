data "archive_file" "lambda" {
  type             = "zip"
  source_dir       = "${path.module}/../../backend/lambda"
  output_path      = "${path.module}/build/lambda.zip"
  output_file_mode = "0644"
  excludes         = ["tests", "__pycache__", ".pytest_cache"]
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/cognito-auth-chatbot"
  retention_in_days = 14
}

resource "aws_iam_role" "lambda_exec" {
  name = "cognito-auth-chatbot-lambda-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# Least-privilege: only this function's own log group, no wildcard resource.
resource "aws_iam_role_policy" "lambda_logs" {
  name = "cognito-auth-chatbot-lambda-logs"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogStream",
        "logs:PutLogEvents",
      ]
      Resource = "${aws_cloudwatch_log_group.lambda.arn}:*"
    }]
  })
}

resource "aws_lambda_function" "chat" {
  function_name = "cognito-auth-chatbot"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "app.lambda_handler"
  runtime       = "python3.13"

  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256

  depends_on = [
    aws_cloudwatch_log_group.lambda,
    aws_iam_role_policy.lambda_logs,
  ]
}
