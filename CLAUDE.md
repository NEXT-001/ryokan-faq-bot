# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Application Overview

This is a Ryokan (Japanese inn) FAQ chatbot built with Streamlit. The application provides semantic search-based automatic responses to common questions about ryokan services, with multi-company support, user authentication, and LINE integration.

## Key Commands

### Development Environment Setup
```bash
# Activate virtual environment (PowerShell)
myenv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Generate embeddings (required on first run or when FAQ data changes)
python -m services.embedding_service

# Start the main application
streamlit run main.py

# Alternative simple test version
streamlit run app.py
```

### Environment Configuration
The application supports both test mode and production mode:
- Test mode: Set `TEST_MODE=true` in .env (no API key required)
- Production mode: Set `ANTHROPIC_API_KEY` and `VOYAGE_API_KEY` in .env

## Architecture

### Core Structure
- `main.py`: Primary application entry point with URL routing and multi-mode support
- `app.py`: Simple test version for basic functionality verification
- `config/settings.py`: Configuration management and API key loading
- `services/`: Core business logic modules
- `core/`: Database and authentication management
- `components/`: UI utilities and shared components
- `utils/`: Helper functions and constants

### Service Layer
- `chat_service.py`: Handles chat responses and semantic search
- `embedding_service.py`: Manages vector embeddings using VoyageAI
- `history_service.py`: Logs and displays interaction history
- `login_service.py`: User authentication and session management
- `company_service.py`: Multi-company data management
- `email_service.py`: Email notifications and verification
- `line_service.py`: LINE Bot integration

### Database Architecture
- SQLite database (`data/faq_database.db`) for user and company data
- Company-specific data stored in `data/companies/{company_id}/`
- Each company has: `faq.csv`, `faq_with_embeddings.pkl`, `history.csv`, `settings.json`

### URL Routing System
The application supports multiple access modes via URL parameters:
- `?mode=user&company_id=demo-company`: User FAQ interface
- `?mode=admin&company_id=demo-company`: Admin management interface
- `?mode=reg`: 14-day trial registration
- `?token=xxx`: Email verification

### Test Mode vs Production Mode
- **Test Mode**: Uses keyword-based responses, no API keys required
- **Production Mode**: Uses Anthropic Claude for responses and VoyageAI for embeddings

## Default Accounts
- Admin: username `admin`, password `admin123`
- Test user: username `user`, password `user` (test mode only)

## Data Management

### FAQ Data Format
FAQ data is stored in CSV format with columns: `question`, `answer`

### Embedding Generation
After updating FAQ data, regenerate embeddings:
```bash
python -m services.embedding_service
```

## Multi-Company Support
The application supports multiple companies with isolated data:
- Each company has a unique ID and separate data directory
- Company-specific FAQ, history, and settings
- Admin users can manage their company's data independently