# ATP Rankings Prediction Challenge

A Streamlit application that tracks and visualizes predictions for the ATP Top 10 rankings in 2025, comparing multiple predictors' accuracy over time.

## Overview

This project tracks how accurately different players predicted the ATP men's tennis rankings. The application:

1. Fetches current ATP rankings data from the ATP Tour website
2. Compares these actual rankings against predictions made by multiple participants
3. Visualizes prediction accuracy over time
4. Provides metrics and statistics about whose predictions are most accurate

## Features

- **Interactive timeline visualization**: See how prediction accuracy evolves over time
- **Key metrics tracking**:
  - Current leader
  - Longest streak as prediction leader
  - Lowest prediction error achieved
  - Best average prediction accuracy
- **Detailed statistics**: Summary table with key performance metrics for all predictors

## Installation

### Prerequisites
- Python 3.8+

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/atp-rankings.git
   cd atp-rankings
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   streamlit run app.py
   ```

## Project Structure

```
atp-rankings/
├── app.py                  # Main Streamlit application
├── requirements.txt        # Project dependencies (for Streamlit app)
├── atp_rankings/
│   └── requirements.txt    # Data collection dependencies
├── .devcontainer/
│   └── devcontainer.json   # VS Code devcontainer configuration
├── LICENSE                 # MIT License
└── README.md               # Project documentation
```

## How It Works

The application:
1. Scrapes ATP rankings data from the official ATP Tour website
2. Calculates the Euclidean distance between predicted and actual rankings
3. Tracks metrics like current leader, longest streak, and lowest error
4. Visualizes changes in prediction accuracy over time using Plotly

## Development in Container

This project includes VS Code devcontainer configuration. To use it:

1. Install Docker and the VS Code Remote - Containers extension
2. Open the project in VS Code
3. Click "Reopen in Container" when prompted
4. The container will set up the development environment automatically

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.