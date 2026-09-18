# Generative AI Project Setup Guide

> **Before you begin:** Make sure you have completed all 'Required Changes' listed in the main README.md. This guide assumes your base Django boilerplate setup is already done.

This guide explains how to extend this Django boilerplate for generative AI projects.

## 1. Install Generative AI Dependencies

Add the following packages to your `config/requirements/base.in` as a recommended starting point. Depending on your project's needs, you may skip some of these or add others:

```
langchain==0.3.*
langchain-core==0.3.*
langchain-community==0.3.*
langchain-openai==0.3.*
langchain-google-genai~=2.0
langchain-anthropic==0.3.*
langgraph==0.4.*
langchain-chroma==0.2.*
langchain-pinecone==0.2.*
```

Then run:

```
make cr
```

## 2. Create and Set Up the AI App

Add a Django app (e.g., `ai`) to organize all generative AI logic. Your app should include the standard Django files and a modular structure for AI components.

### 2.1 AI App Structure

**The following structure is a recommended starting point:**

```
project/
  ai/
    __init__.py
    admin.py
    apps.py
    models.py
    tests.py
    views.py
    urls.py
    serializers.py
    migrations/
    api/
      __init__.py
      v1/
        __init__.py
        serializers.py
        urls.py
        views.py
    # AI-specific directories
    chains/
      __init__.py
    data/
      __init__.py
    graphs/
      __init__.py
    models/
      __init__.py
    nodes/
      __init__.py
    prompts/
      __init__.py
    tools/
      __init__.py
    utils/
      __init__.py
  core/
  users/
  ...
```

## 4. Additional Notes

- Use the AI app to keep all generative AI chains, prompts, tools, and related logic organized and modular.
- All other boilerplate features (Docker, Makefile, Ansible, etc.) remain unchanged.
