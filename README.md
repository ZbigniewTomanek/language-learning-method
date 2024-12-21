# Language Learning Method

A personal project designed to enhance Spanish language learning through automated generation of Anki flashcards and exercises from parsed textbooks using LLMs.

## Features
- Textbook parsing using Ollama and pdf-extract-api
- Anki flashcard generation from parsed content
- Exercise generation based on textbook content
- Flexible LLM integration (default: GPT-4o)

## Prerequisites

Before installation, ensure you have:
- Python 3.8 or higher
- Docker
- Git

## Installation

1. Install uv (Python package installer):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Install Ollama following the instructions at [ollama.ai](https://ollama.ai)

3. Install Docker following the instructions at [docker.com](https://docker.com)

4. Clone the repository and its submodules:
```bash
git clone https://github.com/ZbigniewTomanek/language-learning-method.git
cd language-learning-method
git submodule update --init --recursive
```

## Configuration

By default, the project uses GPT-4o for LLM content generation. Set your OpenAI API key:
```bash
export OPENAI_API_KEY='your-key-here'
```

To configure different LLM settings, use:
```bash
./cli.sh config --help
```

## Usage

### CLI Interface
The project uses Typer for its CLI. To get help for any command:
```bash
./cli.sh --help
```

### Working with Textbooks

1. Add a textbook to the database:
```bash
./cli.sh book add <book-path>
```

2. Start the PDF extraction API:
```bash
./start-pdf-extract-api.sh
```

3. Parse the book:
```bash
./cli.sh parse-pdf <book name>
```

**Note**: The parsing process can be resource-intensive and time-consuming as it utilizes local vision models through Ollama.

### Generating Anki Flashcards

#### From Textbook Content
Generate flashcards from specific pages:
```bash
./cli.sh create-deck-from-book <book-name> <start-page> <end-page> 
```

Example:
```bash
./cli.sh create-deck-from-book life-vision 51 51
```

```bash
./cli.sh create-deck-from-book life-vision 51 51  --custom-llm-prompt "Create deck which help me learn about using as-as comparison, using too and gradation of adjectives. Fiszki powinny być przygotowane dla niezaawansowanej osoby uczącej się angielskiego po polsku"
```

#### From Custom Prompt
Generate flashcards based on a specific prompt:
```bash
./cli.sh create-deck-from-prompt "your prompt here"
```

Example:
```bash
./cli.sh create-deck-from-prompt "Create deck which help me learn about using as-as comparison, using too and gradation of adjectives. Fiszki powinny być przygotowane dla niezaawansowanej osoby uczącej się angielskiego po polsku"
```