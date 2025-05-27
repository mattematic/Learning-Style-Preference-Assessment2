
from flask import Flask, render_template, request, redirect, url_for, session, Response
import os
import json

app = Flask(__name__)
# Ensure FLASK_SECRET_KEY is set in your environment for production, 
# os.urandom(24) is a fallback for development.
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

# Global variables for learning data
LEARNING_STYLES_DATA = []
learning_styles = {}
ALL_QUESTIONS = [] # Flat list of all questions

def load_and_transform_data(file_path='learning_data.json'):
    """Loads data from JSON file and transforms it, and populates ALL_QUESTIONS."""
    global LEARNING_STYLES_DATA, learning_styles, ALL_QUESTIONS
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        transformed_styles = {
            item['style_name']: {
                "questions": item.get("questions", []),
                "recommendations": item.get("recommendations", []),
                "category": item.get("category", "N/A"),
                "description": item.get("description", "N/A")
            }
            for item in data
        }
        LEARNING_STYLES_DATA = data
        learning_styles = transformed_styles
        
        # Populate ALL_QUESTIONS
        temp_questions = []
        question_id_counter = 1
        for style_name, data_val in learning_styles.items():
            for q_text in data_val.get("questions", []):
                temp_questions.append({
                    "id": question_id_counter,
                    "text": q_text,
                    "style": style_name
                })
                question_id_counter += 1
        ALL_QUESTIONS = temp_questions
        app.logger.info(f"Successfully loaded and processed data from {file_path}. {len(ALL_QUESTIONS)} questions loaded.")

    except FileNotFoundError:
        app.logger.error(f"ERROR: '{file_path}' not found. Application will run with no assessment data.")
        LEARNING_STYLES_DATA = []
        learning_styles = {}
        ALL_QUESTIONS = []
    except json.JSONDecodeError:
        app.logger.error(f"ERROR: Failed to decode '{file_path}'. Check syntax. Application will run with no assessment data.")
        LEARNING_STYLES_DATA = []
        learning_styles = {}
        ALL_QUESTIONS = []
    except Exception as e:
        app.logger.error(f"An unexpected error occurred during JSON loading or processing from {file_path}: {e}")
        LEARNING_STYLES_DATA = []
        learning_styles = {}
        ALL_QUESTIONS = []

# Load data on application startup
load_and_transform_data()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/assessment', defaults={'question_num': None}, methods=['GET', 'POST'])
@app.route('/assessment/<int:question_num>', methods=['GET', 'POST'])
def assessment(question_num):
    if not ALL_QUESTIONS:
        app.logger.error("No questions loaded. Assessment cannot proceed.")
        # Pass a specific flag or message to the template to indicate no questions
        return render_template('assessment.html', error_no_questions="Assessment data is unavailable. Please try again later or contact an administrator.")

    if request.method == 'GET':
        if question_num is None:
            # Start of the assessment
            session.pop('assessment_answers', None) # Clear previous answers
            session['assessment_answers'] = {}      # Initialize session storage
            return redirect(url_for('assessment', question_num=1))
        
        # Validate question_num for GET request
        if not (1 <= question_num <= len(ALL_QUESTIONS)):
            app.logger.warning(f"GET request for invalid question number: {question_num}. Redirecting to results.")
            # If answers are present, go to results, else to start.
            if session.get('assessment_answers'):
                 return redirect(url_for('results'))
            return redirect(url_for('assessment', question_num=1))

        current_question_data = ALL_QUESTIONS[question_num - 1]
        existing_answer_data = session.get('assessment_answers', {}).get(str(question_num))
        existing_score = existing_answer_data.get('score') if existing_answer_data else None
        
        return render_template('assessment.html', 
                               current_question=current_question_data,
                               question_num=question_num,
                               total_questions=len(ALL_QUESTIONS),
                               existing_score=existing_score)

    if request.method == 'POST':
        # Validate question_num for POST request (e.g. user manually changed URL)
        if not (1 <= question_num <= len(ALL_QUESTIONS)):
            app.logger.warning(f"POST request for invalid question number: {question_num}. Redirecting to start.")
            return redirect(url_for('assessment', question_num=1))

        score_str = request.form.get('score')
        
        # Validate score
        if not score_str or not score_str.isdigit() or not (1 <= int(score_str) <= 5):
            app.logger.warning(f"Invalid score submitted: '{score_str}' for question {question_num}.")
            current_question_data = ALL_QUESTIONS[question_num - 1]
            existing_answer_data = session.get('assessment_answers', {}).get(str(question_num))
            existing_score = existing_answer_data.get('score') if existing_answer_data else None
            # Re-render the current question page with an error message
            return render_template('assessment.html',
                                   current_question=current_question_data,
                                   question_num=question_num,
                                   total_questions=len(ALL_QUESTIONS),
                                   existing_score=existing_score, # Or the invalid score_str to show it back
                                   error="Please select a valid score between 1 and 5.")

        # Store the answer
        question_id_str = str(question_num)
        assessment_answers = session.get('assessment_answers', {}) # Should have been initialized at GET /assessment
        assessment_answers[question_id_str] = {
            'score': int(score_str),
            'style': ALL_QUESTIONS[question_num - 1]['style']
        }
        session['assessment_answers'] = assessment_answers
        session.modified = True # Ensure session is saved

        # Determine next step
        next_question_num = question_num + 1
        if next_question_num > len(ALL_QUESTIONS):
            return redirect(url_for('results')) # All questions answered
        else:
            return redirect(url_for('assessment', question_num=next_question_num))
    
    # Fallback for safety, though specific methods should be handled above.
    return redirect(url_for('index'))


@app.route('/results', methods=['GET', 'POST']) # Allow GET for redirection from invalid question numbers
def results():
    # Original /results logic was POST only. Now it needs to handle answers from session.
    # If it's a GET request, it might be a redirect from an invalid question number.
    # If no answers in session, redirect to start.
    if request.method == 'GET':
        if not session.get('assessment_answers'):
            app.logger.info("GET request to /results with no assessment answers in session. Redirecting to start.")
            return redirect(url_for('assessment'))
        # If there are answers, proceed to calculate and show results.
        # This assumes that if someone GETs /results, they want to see results from session.

    try:
        if not learning_styles: # Check if learning_styles data failed to load
            app.logger.error("Attempted to calculate results with no learning styles data loaded.")
            return "Error: Assessment data is unavailable. Please contact the administrator.", 500

        submitted_answers = session.get('assessment_answers', {})
        if not submitted_answers:
            app.logger.warning("/results accessed with no answers in session. Redirecting to start assessment.")
            # Optionally, render a message on results page instead of redirecting
            return redirect(url_for('assessment'))

        scores = {}
        for style_name in learning_styles: # Initialize all known styles to 0
            scores[style_name] = 0
        
        for q_id_str, answer_data in submitted_answers.items():
            score = answer_data.get('score')
            style_for_question = answer_data.get('style')
            
            if style_for_question and style_for_question in scores and isinstance(score, int):
                scores[style_for_question] += score
            else:
                app.logger.warning(f"Invalid answer data in session for question_id '{q_id_str}': score={score}, style='{style_for_question}'")

        # Find highest scoring styles
        if not scores: # Should not happen if learning_styles is populated
             app.logger.error("Scores dictionary is empty after processing session answers.")
             # This could happen if learning_styles was empty or answers were malformed.
             # Fallback to avoid error on max() if scores is empty.
             primary_styles = []
             recommendations = {}
        elif not any(s > 0 for s in scores.values()): # All scores are zero or negative (though scores should be positive)
            max_score = 0 
            primary_styles = [] # No primary style if all scores are 0
            recommendations = {}
        else:
            max_score = max(scores.values())
            primary_styles = [style for style, score_val in scores.items() if score_val == max_score and max_score > 0]
            
            recommendations = {}
            for style in primary_styles:
                # Ensure style exists in learning_styles (it should, as scores keys come from learning_styles)
                if style in learning_styles and "recommendations" in learning_styles[style]:
                    recommendations[style] = learning_styles[style]["recommendations"]
                else:
                    app.logger.warning(f"Could not find recommendations for primary style '{style}' in learning_styles.")


        # Store results in session for download (overwrites if already there from a previous run)
        session['assessment_results'] = {
            'scores': scores,
            'primary_styles': primary_styles,
            'recommendations': recommendations,
            'learning_styles_data': learning_styles 
        }
        
        # Clear the raw per-question answers from the session as they are processed
        session.pop('assessment_answers', None)
        session.modified = True # Explicitly mark session as modified after pop

        return render_template('results.html', scores=scores, primary_styles=primary_styles, 
                               recommendations=recommendations, learning_styles=learning_styles)
    
    except ValueError as e: # Should be less likely now with session data, but good to keep
        app.logger.error(f"ValueError during results processing (session data): {e}. Answers: {session.get('assessment_answers')}")
        return "An error occurred while processing your results. Please try taking the assessment again.", 400
    except Exception as e:
        app.logger.error(f"Unexpected error during results processing: {e}. Answers: {session.get('assessment_answers')}")
        return "An unexpected error occurred. Please try again later.", 500

@app.route('/download_results')
def download_results():
    results_data = session.get('assessment_results')
    
    if not results_data:
        app.logger.info("Attempted to download results but no data found in session. Redirecting to index.")
        return redirect(url_for('index')) 

    scores = results_data.get('scores', {})
    primary_styles = results_data.get('primary_styles', [])
    # learning_styles_data is used for descriptions and categories
    learning_styles_data = results_data.get('learning_styles_data', {})

    # Defensive check in case learning_styles_data itself is missing from session, though unlikely if session was set correctly.
    if not learning_styles_data:
        app.logger.error("Learning styles data is missing from session for download. This indicates a problem with session data.")
        return "Error: Could not retrieve complete results data for download. Please try taking the assessment again.", 500

    text_content = "Learning Style Assessment Results\n"
    text_content += "=================================\n\n"

    text_content += "Primary Learning Style(s):\n"
    if primary_styles:
        for style_name in primary_styles:
            description = learning_styles_data.get(style_name, {}).get('description', 'N/A')
            text_content += f"- {style_name}: {description}\n"
    else:
        text_content += "- No primary style identified.\n"
    text_content += "\n"

    text_content += "All Scores:\n"
    if scores:
        for style_name, score_value in scores.items():
            category = learning_styles_data.get(style_name, {}).get('category', 'N/A')
            description = learning_styles_data.get(style_name, {}).get('description', 'N/A')
            text_content += f"- {style_name} ({category}): {score_value}/25\n"
            text_content += f"  Description: {description}\n"
    else:
        text_content += "- No scores available.\n"
    text_content += "\n"

    text_content += "Recommendations:\n"
    if recommendations:
        for style_name, rec_list in recommendations.items():
            if style_name in primary_styles: # Only show recommendations for primary styles
                text_content += f"\nFor {style_name} Learners:\n"
                if rec_list:
                    for rec in rec_list:
                        text_content += f"- {rec}\n"
                else:
                    text_content += "- No specific recommendations for this style.\n"
    else:
        text_content += "- No recommendations available.\n"
    
    text_content += "\n\nReminder: Using techniques from multiple learning preferences often leads to better outcomes."

    return Response(
        text_content,
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment;filename=learning_style_results.txt"}
    )

if __name__ == '__main__':
    # Make sure templates directory exists
    os.makedirs('templates', exist_ok=True)
    
    # Create static directory for CSS
    os.makedirs('static', exist_ok=True)
    
    # Start the app
    app.run(host='0.0.0.0', port=8080)
