# Backend Folder Documentation

This document describes the purpose of every folder and major file in the backend. It serves as a guide for future developers so they can quickly understand the project structure, know where new code belongs, and maintain a consistent architecture.

---

# Architecture Philosophy

The backend follows a **layered FastAPI architecture** with a clear separation of responsibilities.

The guiding principles are:

* One responsibility per module.
* Business logic separated from API routing.
* Provider implementations isolated from application logic.
* Shared utilities centralized.
* Configuration managed from a single location.
* Easy navigation for future contributors.
* Production-ready organization without changing application behavior.

The structure is designed so that new features can be added without creating tightly coupled modules or scattered logic.

---

# Directory Structure

```text
.
├── backend/
│   ├── .env
│   ├── main.py
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       ├── api/
│       ├── core/
│       ├── providers/
│       ├── services/
│       └── utils/
├── mcp/
│   ├── shared/
│   │   ├── base.py
│   │   ├── registry.py
│   │   └── utils.py
│   └── memory/
│       ├── pyproject.toml
│       ├── server.py
│       ├── handlers.py
│       ├── tools.py
|       ├── test_client.py
│       ├── config.py
│       └── core/
│           ├── engine.py
│           ├── extractor.py
│           ├── deduplicator.py
│           ├── contradiction.py
│           ├── confidence.py
│           ├── importance.py
│           ├── storage.py
│           ├── vector_store.py
│           ├── markdown.py
│           ├── retrieval.py
│           ├── models.py
│           └── schemas.py
├── data/
├── tests/
├── docker-compose.yml
└── Dockerfile
```

---

# Root Directory

The root of the backend contains files responsible for starting the application, storing configuration, and housing project-wide resources.

---

## `.env`

Purpose:

Stores runtime configuration and secrets.

Typical contents include:

* API keys
* Default provider
* Default model
* Environment variables
* Memory configuration
* Feature toggles

This file should **never** contain application logic.

---

## `main.py`

Purpose:

Acts as the application's root entrypoint.

Responsibilities:

* Starts the FastAPI server.
* Imports the application instance from `app.main`.
* Preserves compatibility with development scripts and deployment tooling.
* Contains minimal logic.

This file should remain lightweight.

---

# `app/`

The `app` package contains the actual backend implementation.

Everything related to application logic lives here.

---

## `app/main.py`

Purpose:

Creates and configures the FastAPI application.

Responsibilities include:

* Creating the FastAPI app instance.
* Registering middleware.
* Configuring CORS.
* Registering API routers.
* Initializing application startup components.
* Preparing the application for serving requests.

This file should contain application wiring only and should avoid business logic.

---

# `app/api/`

Purpose:

Contains the HTTP layer of the application.

This package is responsible for exposing functionality through REST endpoints.

The API layer should only:

* Receive requests.
* Validate inputs.
* Call appropriate services.
* Return responses.

It should **not** contain business logic.

---

## `app/api/routes/`

Purpose:

Contains endpoint definitions grouped by feature.

Each file represents one logical area of the API.

Current structure:

```text
routes/
├── auth.py
├── chat.py
└── memory.py
```

### `auth.py`

Responsible for:

* Provider configuration endpoints.
* API key verification.
* Configuration management.

---

### `chat.py`

Responsible for:

* Chat-related endpoints.
* User conversations.
* Model interaction requests.

---

### `memory.py`

Responsible for:

* Memory configuration.
* Compression endpoints.
* Memory statistics.
* Memory management operations.

---

# `app/core/`

Purpose:

Contains application-wide core functionality.

Anything required by multiple modules belongs here.

This folder should **not** contain endpoint-specific logic.

Current files:

```text
core/
├── config.py
└── prompts.py
```

---

## `config.py`

Central location for application configuration.

Responsibilities include:

* Reading environment variables.
* Writing configuration.
* Loading saved provider settings.
* Managing memory configuration.
* Centralizing configuration access.

Any module requiring configuration should obtain it from here instead of reading files directly.

---

## `prompts.py`

Contains all LLM prompt templates used by the application.

Examples include:

* Compression prompts
* Grounding prompts
* Initial conversation prompts
* Prompt constants

Keeping prompts centralized makes them easier to update and maintain.

---

# `app/providers/`

Purpose:

Contains integrations for every supported AI provider.

The rest of the application interacts with providers through a common interface instead of directly calling provider-specific implementations.

This design makes adding new providers straightforward while keeping the rest of the codebase unchanged.

Current structure:

```text
providers/
├── base.py
├── factory.py
├── openai.py
├── gemini.py
├── anthropic.py
├── ...
```

---

## `base.py`

Defines the common provider interface.

Every provider implementation should inherit from this base class or follow its contract.

This ensures all providers expose a consistent API to the application.

---

## `factory.py`

Responsible for selecting and creating the correct provider implementation based on configuration.

The rest of the backend should never instantiate provider classes directly.

Instead, they should request a provider from the factory.

---

## Provider Adapters

Each provider file contains the implementation specific to one AI provider.

Examples:

* OpenAI
* Gemini
* Anthropic
* Groq
* Mistral
* Together AI
* Cohere
* Hugging Face
* DeepSeek
* OpenRouter
* Fireworks AI
* AI21
* Cerebras
* NVIDIA NIM
* DeepInfra

Each adapter is responsible only for translating the application's requests into the provider's API.

Provider-specific code should never leak into services or API routes.

---

# `app/services/`

Purpose:

Contains the application's business logic.

Services coordinate work between:

* API routes
* Providers
* Utilities
* Configuration
* Storage

API routes should remain thin and delegate processing to services.

Current structure:

```text
services/
├── compression.py
└── telemetry.py
```

---

## `compression.py`

Responsible for:

* Conversation compression.
* Context summarization.
* Token optimization.
* Compression workflow orchestration.
* LLM compression requests.

This module contains the core logic related to memory compression.

---

## `telemetry.py`

Responsible for:

* Memory statistics.
* Compression metrics.
* Session analytics.
* Event reporting.
* Runtime statistics generation.

Telemetry should focus on collecting and exposing operational metrics rather than implementing business workflows.

---

# `app/utils/`

Purpose:

Contains reusable helper modules.

Utilities should be:

* Stateless where possible.
* Generic.
* Shared across multiple services.
* Independent of HTTP requests.

Current structure:

```text
utils/
├── storage.py
└── token.py
```

---

## `storage.py`

Responsible for interacting with persistent storage used by the memory system.

Responsibilities may include:

* Reading facts.
* Writing facts.
* Managing storage locations.
* Saving generated data.
* Loading persisted information.

This module abstracts storage operations from higher-level services.

---

## `token.py`

Responsible for token-related utilities.

Examples include:

* Token counting.
* Token estimation.
* Context size calculations.
* Payload optimization helpers.

Any tokenizer-specific functionality should remain isolated here.

---

# `data/`

Purpose:

Contains persistent application data.

Examples include:

* Stored facts.
* Memory files.
* Cached application data.
* Generated artifacts.

Business logic should not be implemented inside this directory.

It should contain data only.

---

# `tests/`

Purpose:

Contains automated tests for the backend.

Current structure:

```text
tests/
└── provider_test.py
```

Tests should verify application behavior without modifying production code.

As the project grows, additional test modules should be added for:

* API routes
* Services
* Utilities
* Providers
* Memory system
* Compression
* Configuration

---

# Dependency Flow

The intended dependency direction is:

```text
HTTP Request
      │
      ▼
API Routes
      │
      ▼
Services
      │
 ┌────┼──────────┐
 ▼    ▼          ▼
Core Providers Utils
      │
      ▼
External AI APIs

Services
      │
      ▼
Data Storage
```

Higher layers should depend on lower layers.

Lower layers should never depend on higher layers.

For example:

* Services should not import API routes.
* Providers should not import services.
* Utilities should not import routes.

Maintaining this dependency direction keeps the architecture modular and prevents circular dependencies.

---

# Guidelines for Future Development

When adding new functionality:

* Add new endpoints inside `app/api/routes/`.
* Place business logic inside `app/services/`.
* Add reusable helpers to `app/utils/`.
* Add new provider integrations to `app/providers/`.
* Store shared configuration in `app/core/`.
* Keep `app/main.py` limited to application initialization.
* Keep `backend/main.py` as a lightweight entrypoint.

Avoid placing business logic inside route handlers or utility modules.

---

# Design Principles

The backend follows these architectural principles:

* Single Responsibility Principle (SRP)
* Separation of Concerns
* Layered Architecture
* Modular Design
* Clear Dependency Direction
* Minimal Coupling
* High Cohesion
* Production-Ready Organization
* Zero Hidden Business Logic
* Predictable File Placement

Following these conventions ensures that the backend remains maintainable, scalable, and easy for new developers to understand as the project evolves.
