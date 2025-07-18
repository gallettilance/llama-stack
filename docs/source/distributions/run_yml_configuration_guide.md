# Llama Stack run.yml Configuration Guide

## Overview

The `run.yml` file is the core configuration file for Llama Stack distributions. It defines which APIs are enabled, which providers to use for each API, and how to configure those providers. This guide covers everything you need to know to configure your `run.yml` file effectively.

## Basic Structure

A minimal `run.yml` file has the following structure:

```yaml
version: 2
image_name: your-distribution-name
apis:
- inference
- safety
- agents
providers:
  inference:
  - provider_id: ollama
    provider_type: remote::ollama
    config:
      url: ${env.OLLAMA_URL:=http://localhost:11434}
  safety:
  - provider_id: llama-guard
    provider_type: inline::llama-guard
    config:
      excluded_categories: []
  agents:
  - provider_id: meta-reference
    provider_type: inline::meta-reference
    config:
      persistence_store:
        type: sqlite
        db_path: ${env.SQLITE_STORE_DIR:=~/.llama/distributions/your-distribution}/agents_store.db
```

## Configuration Sections

### 1. Version and Image Name

```yaml
version: 2  # Always use version 2 for current Llama Stack
image_name: your-distribution-name  # Unique identifier for your distribution
```

### 2. APIs

The `apis` section defines which Llama Stack APIs are enabled:

```yaml
apis:
- agents          # Agent management and execution
- datasetio       # Dataset input/output operations
- eval            # Model evaluation and benchmarking
- files           # File management
- inference       # Model inference (chat completion, embeddings)
- post_training   # Post-training operations
- safety          # Content safety and filtering
- scoring         # Model scoring functions
- telemetry       # Observability and tracing
- tool_runtime    # Tool execution
- vector_io       # Vector database operations
```

### 3. Providers

The `providers` section is the most important part, defining which providers to use for each API:

```yaml
providers:
  inference:
  - provider_id: ollama
    provider_type: remote::ollama
    config:
      url: ${env.OLLAMA_URL:=http://localhost:11434}
  
  vector_io:
  - provider_id: faiss
    provider_type: inline::faiss
    config:
      kvstore:
        type: sqlite
        db_path: ${env.SQLITE_STORE_DIR:=~/.llama/distributions/your-distribution}/faiss_store.db
```

## Provider Types

### Remote Providers

Remote providers connect to external services:

```yaml
# OpenAI
- provider_id: openai
  provider_type: remote::openai
  config:
    api_key: ${env.OPENAI_API_KEY}

# Anthropic
- provider_id: anthropic
  provider_type: remote::anthropic
  config:
    api_key: ${env.ANTHROPIC_API_KEY}

# Ollama
- provider_id: ollama
  provider_type: remote::ollama
  config:
    url: ${env.OLLAMA_URL:=http://localhost:11434}

# vLLM
- provider_id: vllm
  provider_type: remote::vllm
  config:
    url: ${env.VLLM_URL}
    max_tokens: ${env.VLLM_MAX_TOKENS:=4096}
    api_token: ${env.VLLM_API_TOKEN:=fake}
    tls_verify: ${env.VLLM_TLS_VERIFY:=true}
```

### Inline Providers

Inline providers run within the Llama Stack process:

```yaml
# Meta Reference (for inference)
- provider_id: meta-reference-inference
  provider_type: inline::meta-reference
  config:
    model: ${env.INFERENCE_MODEL}
    checkpoint_dir: ${env.INFERENCE_CHECKPOINT_DIR:=null}
    quantization:
      type: ${env.QUANTIZATION_TYPE:=bf16}
    model_parallel_size: ${env.MODEL_PARALLEL_SIZE:=0}
    max_batch_size: ${env.MAX_BATCH_SIZE:=1}
    max_seq_len: ${env.MAX_SEQ_LEN:=4096}

# Llama Guard (for safety)
- provider_id: llama-guard
  provider_type: inline::llama-guard
  config:
    excluded_categories: []

# FAISS (for vector storage)
- provider_id: faiss
  provider_type: inline::faiss
  config:
    kvstore:
      type: sqlite
      db_path: ${env.SQLITE_STORE_DIR:=~/.llama/distributions/your-distribution}/faiss_store.db
```

## Environment Variable Substitution

Llama Stack supports powerful environment variable substitution:

### Basic Syntax

```yaml
config:
  api_key: ${env.API_KEY}  # Required - will error if not set
  url: ${env.SERVICE_URL}   # Required - will error if not set
```

### Default Values

```yaml
config:
  url: ${env.OLLAMA_URL:=http://localhost:11434}  # Default if not set
  port: ${env.PORT:=8321}                          # Default if not set
  timeout: ${env.TIMEOUT:=60}                      # Default if not set
```

### Conditional Values

```yaml
config:
  # Only include if ENVIRONMENT is set
  environment: ${env.ENVIRONMENT:+production}
  
  # Only include if DEBUG is set
  debug_mode: ${env.DEBUG:+true}
```

### Empty Defaults

```yaml
config:
  # Becomes None if not set
  optional_token: ${env.OPTIONAL_TOKEN:+}
```

## Storage Configuration

### SQLite Storage

```yaml
config:
  kvstore:
    type: sqlite
    db_path: ${env.SQLITE_STORE_DIR:=~/.llama/distributions/your-distribution}/store.db
```

### PostgreSQL Storage

```yaml
config:
  persistence_store:
    type: postgres
    host: ${env.POSTGRES_HOST:=localhost}
    port: ${env.POSTGRES_PORT:=5432}
    db: ${env.POSTGRES_DB:=llamastack}
    user: ${env.POSTGRES_USER:=llamastack}
    password: ${env.POSTGRES_PASSWORD:=llamastack}
```

## Authentication Configuration

### OAuth2 Token Authentication

```yaml
server:
  port: 8321
  auth:
    provider_config:
      type: "oauth2_token"
      jwks:
        uri: "https://your-token-issuer.com/jwks"
      audience: "llama-stack"
      issuer: "https://your-token-issuer.com"
```

### Custom Authentication

```yaml
server:
  port: 8321
  auth:
    provider_config:
      type: "custom"
      endpoint: "https://your-auth-service.com/validate"
```

## Complete Example Configurations

### Simple Ollama Configuration

```yaml
version: 2
image_name: ollama-simple
apis:
- inference
- safety
- agents
providers:
  inference:
  - provider_id: ollama
    provider_type: remote::ollama
    config:
      url: ${env.OLLAMA_URL:=http://localhost:11434}
  safety:
  - provider_id: llama-guard
    provider_type: inline::llama-guard
    config:
      excluded_categories: []
  agents:
  - provider_id: meta-reference
    provider_type: inline::meta-reference
    config:
      persistence_store:
        type: sqlite
        db_path: ${env.SQLITE_STORE_DIR:=~/.llama/distributions/ollama-simple}/agents_store.db
      responses_store:
        type: sqlite
        db_path: ${env.SQLITE_STORE_DIR:=~/.llama/distributions/ollama-simple}/responses_store.db
```

### Production Configuration with Multiple Providers

```yaml
version: 2
image_name: production-stack
apis:
- agents
- inference
- safety
- telemetry
- tool_runtime
- vector_io
providers:
  inference:
  - provider_id: openai
    provider_type: remote::openai
    config:
      api_key: ${env.OPENAI_API_KEY}
  - provider_id: anthropic
    provider_type: remote::anthropic
    config:
      api_key: ${env.ANTHROPIC_API_KEY}
  - provider_id: sentence-transformers
    provider_type: inline::sentence-transformers
    config: {}
  vector_io:
  - provider_id: chromadb
    provider_type: remote::chromadb
    config:
      url: ${env.CHROMADB_URL}
  - provider_id: faiss
    provider_type: inline::faiss
    config:
      kvstore:
        type: sqlite
        db_path: ${env.SQLITE_STORE_DIR:=~/.llama/distributions/production-stack}/faiss_store.db
  safety:
  - provider_id: llama-guard
    provider_type: inline::llama-guard
    config:
      excluded_categories: []
  agents:
  - provider_id: meta-reference
    provider_type: inline::meta-reference
    config:
      persistence_store:
        type: postgres
        host: ${env.POSTGRES_HOST:=localhost}
        port: ${env.POSTGRES_PORT:=5432}
        db: ${env.POSTGRES_DB:=llamastack}
        user: ${env.POSTGRES_USER:=llamastack}
        password: ${env.POSTGRES_PASSWORD:=llamastack}
      responses_store:
        type: postgres
        host: ${env.POSTGRES_HOST:=localhost}
        port: ${env.POSTGRES_PORT:=5432}
        db: ${env.POSTGRES_DB:=llamastack}
        user: ${env.POSTGRES_USER:=llamastack}
        password: ${env.POSTGRES_PASSWORD:=llamastack}
  telemetry:
  - provider_id: meta-reference
    provider_type: inline::meta-reference
    config:
      service_name: "${env.OTEL_SERVICE_NAME:=llama-stack}"
      sinks: ${env.TELEMETRY_SINKS:=console,otel_trace}
      otel_trace_endpoint: ${env.OTEL_TRACE_ENDPOINT:=http://localhost:4318/v1/traces}
  tool_runtime:
  - provider_id: meta-reference
    provider_type: inline::meta-reference
    config: {}
server:
  port: 8321
  auth:
    provider_config:
      type: "oauth2_token"
      jwks:
        uri: "https://your-auth-provider.com/jwks"
      audience: "llama-stack"
      issuer: "https://your-auth-provider.com"
```

## Advanced Configuration Options

### External Providers Directory

```yaml
external_providers_dir: ${env.EXTERNAL_PROVIDERS_DIR:=~/.llama/providers.d}
```

### Logging Configuration

```yaml
logging_config:
  level: ${env.LOG_LEVEL:=INFO}
  format: ${env.LOG_FORMAT:=json}
  sinks: ${env.LOG_SINKS:=console}
```

### Models Registration

```yaml
models:
- metadata: {}
  model_id: ${env.INFERENCE_MODEL}
  provider_id: ollama
  provider_model_id: null
```

### Shields Configuration

```yaml
shields:
- metadata: {}
  shield_id: llama-guard
  provider_id: llama-guard
  provider_shield_id: null
```

## Environment Variables Reference

### Common Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_URL` | Ollama server URL | `http://localhost:11434` |
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `ANTHROPIC_API_KEY` | Anthropic API key | Required |
| `INFERENCE_MODEL` | Model to use for inference | Required |
| `SAFETY_MODEL` | Model to use for safety checks | Required |
| `SQLITE_STORE_DIR` | SQLite database directory | `~/.llama/distributions/{image_name}` |
| `POSTGRES_HOST` | PostgreSQL host | `localhost` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `POSTGRES_DB` | PostgreSQL database | `llamastack` |
| `POSTGRES_USER` | PostgreSQL user | `llamastack` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `llamastack` |
| `OTEL_SERVICE_NAME` | OpenTelemetry service name | `llama-stack` |
| `OTEL_TRACE_ENDPOINT` | OpenTelemetry trace endpoint | `http://localhost:4318/v1/traces` |

### Provider-Specific Environment Variables

#### vLLM
- `VLLM_URL`: vLLM server URL
- `VLLM_MAX_TOKENS`: Maximum tokens for generation
- `VLLM_API_TOKEN`: API token for vLLM
- `VLLM_TLS_VERIFY`: TLS verification setting

#### NVIDIA
- `NVIDIA_BASE_URL`: NVIDIA API base URL
- `NVIDIA_API_KEY`: NVIDIA API key
- `NVIDIA_APPEND_API_VERSION`: Whether to append API version

#### Hugging Face
- `HF_API_TOKEN`: Hugging Face API token
- `INFERENCE_MODEL`: Model repository name

## Running with Configuration

### Using a Configuration File

```bash
# Run with a specific config file
llama stack run --config run.yaml --port 8321

# Run with environment variables
llama stack run --config run.yaml \
  --env OPENAI_API_KEY=sk-123 \
  --env INFERENCE_MODEL=gpt-4 \
  --port 8321
```

### Using a Template

```bash
# Run using a built-in template
llama stack run starter --port 8321

# Run with template and environment variables
llama stack run starter \
  --env OPENAI_API_KEY=sk-123 \
  --env INFERENCE_MODEL=gpt-4 \
  --port 8321
```

## Best Practices

### 1. Use Environment Variables for Secrets

```yaml
# Good
config:
  api_key: ${env.OPENAI_API_KEY}

# Bad
config:
  api_key: sk-1234567890abcdef
```

### 2. Provide Sensible Defaults

```yaml
config:
  url: ${env.OLLAMA_URL:=http://localhost:11434}
  port: ${env.PORT:=8321}
  timeout: ${env.TIMEOUT:=60}
```

### 3. Use Conditional Configuration

```yaml
# Only enable providers when needed
- provider_id: ${env.ENABLE_CHROMADB:+chromadb}
  provider_type: remote::chromadb
  config:
    url: ${env.CHROMADB_URL}
```

### 4. Organize by Environment

Create separate configuration files for different environments:

```
configs/
├── dev-run.yaml
├── staging-run.yaml
└── prod-run.yaml
```

### 5. Document Your Configuration

Add comments to explain complex configurations:

```yaml
providers:
  inference:
  # Primary inference provider
  - provider_id: openai
    provider_type: remote::openai
    config:
      api_key: ${env.OPENAI_API_KEY}
  
  # Fallback inference provider
  - provider_id: anthropic
    provider_type: remote::anthropic
    config:
      api_key: ${env.ANTHROPIC_API_KEY}
```

## Troubleshooting

### Common Issues

1. **Missing Environment Variables**
   ```bash
   # Error: Environment variable OPENAI_API_KEY not set
   # Solution: Set the environment variable
   export OPENAI_API_KEY=your-api-key
   ```

2. **Invalid Provider Type**
   ```yaml
   # Error: Unknown provider type 'remote::invalid'
   # Solution: Check provider type spelling
   provider_type: remote::openai  # Correct
   ```

3. **Database Connection Issues**
   ```yaml
   # Error: Cannot connect to PostgreSQL
   # Solution: Check database configuration
   config:
     host: ${env.POSTGRES_HOST:=localhost}
     port: ${env.POSTGRES_PORT:=5432}
     db: ${env.POSTGRES_DB:=llamastack}
     user: ${env.POSTGRES_USER:=llamastack}
     password: ${env.POSTGRES_PASSWORD:=llamastack}
   ```

### Validation

Validate your configuration before running:

```bash
# Check if the configuration file is valid
llama stack run --config run.yaml --dry-run
```

### Debug Mode

Enable debug logging to troubleshoot issues:

```bash
llama stack run --config run.yaml --env LOG_LEVEL=DEBUG
```

This comprehensive guide should help you configure your `run.yml` file effectively for any Llama Stack deployment scenario. 