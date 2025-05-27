# Learning Style Preference Assessment

## Description
This web application helps users identify their preferred learning style(s) through a questionnaire. Based on their responses, it provides personalized recommendations and a breakdown of their scores across various learning style categories. The assessment is presented one question at a time for a focused experience.

## Features
*   **Learning Style Assessment:** Users answer a series of questions to determine their dominant learning styles.
*   **Paginated Questions:** Assessment questions are presented one at a time for better focus.
*   **Personalized Recommendations:** Tailored suggestions are provided based on the identified primary learning style(s).
*   **Score Breakdown:** Users can see their scores for all assessed learning styles (Visual, Auditory, Reading/Writing, Kinesthetic, Deep Learning, Strategic Learning).
*   **Download Results:** Assessment results can be downloaded as a plain text file.
*   **Responsive Design:** The application is designed to be usable on different screen sizes.

## Setup Instructions

### Prerequisites
*   Python 3.7 or higher
*   pip (Python package installer)

### Installation
1.  **Clone the repository (if applicable):**
    If you obtained the code as a Git repository, clone it using:
    ```bash
    git clone your_repository_url
    cd your_project_directory_name
    ```
    *(Note: If running in an environment like Replit or if you downloaded the code directly, cloning might not be necessary, and files are already present.)*

2.  **Install dependencies:**
    This project uses Flask. Install it using pip:
    ```bash
    pip install Flask
    ```

### Running the Application
1.  Navigate to the project's root directory (where `main.py` is located).
2.  Run the application using the following command:
    ```bash
    python main.py
    ```
3.  Open your web browser and go to `http://0.0.0.0:8080/` or `http://localhost:8080/`.

## Usage
1.  Open the application in your web browser.
2.  Click "Start Assessment" on the home page.
3.  Answer each question on a scale of 1 (Strongly Disagree) to 5 (Strongly Agree).
4.  Use the "Next Question" button to proceed. You can use the "Previous Question" button to go back and change an answer.
5.  After the last question, click "View Results".
6.  The results page will display your primary learning style(s), a full score breakdown, and tailored recommendations.
7.  You can download your results using the "Download Results as Text" button.

## Project Structure (Simplified)
```
.
├── main.py             # Main Flask application logic
├── learning_data.json  # Contains questions, styles, and recommendations
├── static/
│   └── style.css       # CSS styles
├── templates/
│   ├── index.html      # Home page
│   ├── assessment.html # Assessment page (single question view)
│   └── results.html    # Results display page
├── tests/
│   └── test_main.py    # Unit tests
└── README.md           # This file
```
