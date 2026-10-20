# 🤖 Automated Hub

**Business Automation Pipeline & Intelligence Platform.**

> ⚠️ **Note:** This is a portfolio project demonstrating Python automation, Data Analysis, and AI integration capabilities.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Gemini](https://img.shields.io/badge/AI-Gemini_Pro-8E75B2?logo=google-gemini&logoColor=white)
![Automation](https://img.shields.io/badge/DevOps-Automation-blue)

## 📖 Overview

**Automated Hub** is a centralized system designed to automate the entire lifecycle of content creation and business operations. It integrates trend analysis across multiple platforms, generates AI-driven content tailored to a specific brand voice, and manages SNS interactions automatically.

It serves as a "Digital Staff" that works 24/7 to monitor the market and engage with the audience.

## 🏗 Architecture

```mermaid
graph TD
    subgraph "🔍 Input / Research"
        YouTube[YouTube API]
        Trends[Google Trends]
        News[Tech News RSS]
    end

    subgraph "🧠 Core Engine (Python)"
        Crawler[Data Crawler]
        Analyzer[Trend Analyzer]
        Generator[AI Content Generator]
        Manager[Workflow Manager]
    end

    subgraph "💾 Data & Config"
        DB[(Analytics DB)]
        Profile[Profile Config]
    end

    subgraph "🚀 Output"
        X[X (Twitter)]
        Blog[Tech Blog]
        Report[Daily Report]
    end

    YouTube & Trends & News --> Crawler
    Crawler --> Analyzer
    Analyzer --> Generator
    Profile -.-> Generator
    Generator --> Manager
    Manager --> X & Blog & Report
    Analyzer -.-> DB
```

## ✨ Key Features

### 1. 📊 Trend Analysis
- **Multi-Source Monitoring:** Aggregates data from YouTube, Google Trends, and Tech News.
- **Pattern Recognition:** Identifies rising topics in "AI" and "EdTech" sectors.
- **Competitor Analysis:** Tracks competitor activities and market positioning.

### 2. 📝 AI Content Generation
- **Persona-Based Writing:** Generates posts mimicking the developer's specific tone (casual, no emojis, etc.) defined in `profile.json`.
- **Context Awareness:** References past projects (Encura, Vidnitive) to create relevant context.
- **Multi-Format Output:** Creates content for X (Twitter), Blog posts, and Video scripts.

### 3. 🔄 Workflow Automation
- **Daily Routine:** Automatically executes morning checks and evening reports.
- **Notification Sync:** Integrates with Calendar and Slack/Discord for alerts.

## 🛠 Tech Stack

*   **Language:** Python 3.10+
*   **AI Model:** Google Gemini Pro (via `google-generativeai`)
*   **APIs:**
    *   YouTube Data API v3
    *   Google Trends (pytrends)
    *   X API (Tweepy)
*   **Data:** JSON / SQLite (for lightweight storage)

## 🚀 Setup

1.  **Clone the repository**
    ```bash
    git clone https://github.com/naki0227/AutomatedHub.git
    cd AutomatedHub
    ```

2.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure environment**
    ```bash
    cp .env.example .env
    # Edit .env with your API Keys (GEMINI_API_KEY, etc.)
    
    cp profile.example.json profile.json
    # Edit profile.json with your brand details
    ```

4.  **Run scripts**
    ```bash
    # Run the daily routine
    python scripts/daily_routine.py
    
    # Generate content manually
    python scripts/generate_content.py --topic "Gemini 2.0"
    ```

## 📂 Project Structure

```
automated/
├── core/          # Core configuration and utilities
├── analytics/     # Trend analysis modules (YouTube, TikTok, etc.)
├── ai/            # AI integration (Gemini Client, Content Generator)
├── sns/           # SNS platform integrations
├── business/      # Business logic and reporting
├── notifications/ # Notification system
├── scripts/       # Executable entry points
└── profile.json   # Brand personality configuration (Ignored in Git)
```

## 👨‍💻 Developer

**Ibuki Nagase** (Enludus)
*   Portfolio: [https://enludus.com](https://enludus.com)
*   GitHub: [@naki0227](https://github.com/naki0227)

---
© 2025 Enludus. All rights reserved.
