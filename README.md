# Lego

Build scalable, maintainable, performant webapps one block at a time.

## Overview

Lego is a modular Python web framework designed to help developers build modern web applications with a component-based approach. It combines the power of FastHTML and MonsterUI with an authentication system and a clean architecture to create performant, maintainable web applications.

## Features

- 🧩 **Modular Architecture**: Build your application block by block, like Lego
- 🔒 **Built-in Authentication**: Complete auth system with login, registration, password reset
- 🎨 **Modern UI Components**: Responsive UI components with MonsterUI
- 🚀 **Fast Rendering**: Optimized HTML rendering with FastHTML
- 🌓 **Theme Support**: Light/dark mode and customizable themes
- 💾 **SQLite Database**: Simple database integration with WAL mode for performance

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/lego.git
cd lego

# Using Poetry (recommended)
poetry install
```

## Quickstart

1. **Start the server**

```bash
python app.py
```

2. **Visit your application**

Open your browser and navigate to: http://localhost:5001

## Project Structure

```
lego/
├── app.py              # Main application entry point
├── auth/               # Authentication module (example block)
│   ├── app.py          # Auth routes and connections
│   ├── cfg.py          # Auth configuration
│   ├── data.py         # Auth data models and logic
│   └── ui.py           # Auth UI components
├── core/               # Core functionality
│   ├── cfg.py          # Core configuration
│   └── ui.py           # UI components and helpers
├── db/                 # Database files
├── static/             # Static assets
└── pyproject.toml      # Project dependencies
```

## Philosophy

Lego is built on the concept of modular, composable blocks. Each block can:

- Be completely standalone(own config, database, dependencies)
- Build on top of other blocks(use existing databases, config from one or more components)
- Partially depend on other blocks(use some of the blocks' config or helper methods)

This approach allows you to create reusable components that can be mixed and matched to build different applications while maintaining clean separation of concerns.

## Creating Your First Block

Lego follows a modular approach where each feature is a "block" that can be connected to the main application:

1. Create a new directory for your block (e.g., `myblock/`)
2. Create the following files in your block:
   - `__init__.py` - Export your `connect` function
   - `app.py` - Define your routes and `connect` function
   - `cfg.py` - Configuration for your block
   - `ui.py` - Create UI components
   - `data.py` - Define data models and logic

3. Connect your block in `app.py`:

```python
import myblock

# connect your blocks. you can override the routes in blocks placed before the last one
myblock.connect(app)
```

## Example Block Structure

The auth block provides a complete authentication system that can be easily connected to your app:

```python
# In auth/app.py
def connect(app, prefix="/a"):
    setup_oath(app)
    app.before.append(before)
    Routes.base = prefix
    app.get("/")(welcome)
    app.get(Routes.login)(login)
    app.post(Routes.login)(process_login)
    # ... more routes
```

## Code Style

Lego follows the fast.ai coding style:

- Concise, expressive code
- Focus on readability and maintainability
- Avoid unnecessary abstractions
- Does NOT use ruff or black for formatting

## Configuration

Configuration is managed through `.env.override` files in the project root and module directories. Default configurations are in `core/cfg.py`.

## Roadmap
- 📨 **Email integration**: Add support for sending emails with forgot password, verification emails, and self-hosted email server with emailwiz
- 📝 **Logging**: Add structured logging and support for multiple logging targets
- 🗄️ **PostgreSQL support**: Add support for PostgreSQL databases
- 📊 **Admin dashboard**: Built-in admin interface for managing application data
- 🧪 **Testing utilities**: Helpers for testing blocks and components
- 📚 **Documentation generator**: Automatic documentation for blocks and APIs

## Target Audience

Lego is designed for:

- **Web Developers** who want a modular, component-based approach to building web applications
- **Python Developers** looking for a modern alternative to traditional web frameworks
- **Rapid Prototypers** who need to quickly build functional web applications with authentication
- **Teams** that want to organize code into reusable, maintainable blocks

## License

MIT
