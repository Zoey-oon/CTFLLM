# CTF-Agent

CTF-Agent is an intelligent assistant powered by Large Language Models (LLMs) designed to help solve CTF (Capture The Flag) challenges. It supports multiple LLM services and can work in both automatic and human-in-the-loop modes.

## Features

- Multiple LLM service support (DeepSeek, OpenAI GPT, Anthropic Claude)
- Interactive configuration and setup
- Automatic and Human-In-The-Loop (HITL) solving modes
- Smart prompt construction based on challenge type
- Comprehensive error handling and retry mechanisms

## Prerequisites

- Python 3.x
- pip (Python package installer)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/ctf-agent.git
cd ctf-agent
```

2. Set up Python virtual environment:
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate
```

3. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Basic Usage

1. Start the program:
```bash
python main.py
```

2. Interactive Mode Selection:
   - The program will present two modes:
     * Auto Mode (1): Fully automated solving
     * HITL Mode (2): Human in the Loop - allows you to interact with and guide the solving process
   
3. Challenge Input:
   - Choose between:
     * Manual Input (1): Directly input challenge details
     * Load from Local Directory (2): Select from existing challenges

4. LLM Service Selection:
   - Available models:
     * DeepSeek (Recommended)
     * OpenAI GPT
     * Anthropic Claude
   - Enter your API key when prompted
   - API keys are only needed once per session

5. Solving Process:
   - Auto Mode: 
     * Automatically analyzes and solves the challenge
     * Shows progress and intermediate results
     * Saves solution in the challenges directory
   
   - HITL Mode:
     * Allows you to interact with the solving process
     * You can provide additional prompts and guidance
     * More control over the solution approach

Note: The program will automatically handle API configuration during the first run. No manual configuration is needed beforehand.

## Output Structure

Results are saved in the following structure:
```
challenges/
└── {year}/
    └── {category}/
        └── {challenge_name}/
            ├── {challenge_name}.json           # Challenge information
            └── {challenge_name}_solution.json  # LLM solution
```

## Troubleshooting

- **API Connection Failed**: Verify API key and network connection
- **Poor Solution Quality**: Try a different model or use HITL mode
- **Rate Limiting**: Check API quota and limits
- **Authorization Error**: Ensure API key is valid and not expired

## Recommended LLM Services

- **DeepSeek** (Recommended): Excellent code understanding and CTF solving capabilities
- **OpenAI GPT**: Strong reasoning and problem-solving abilities
- **Anthropic Claude**: Superior logical reasoning and security focus

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines Here]
