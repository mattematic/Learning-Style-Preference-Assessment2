
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

def load_and_transform_data(file_path='learning_data.json'):
    """Loads data from JSON file and transforms it."""
    global LEARNING_STYLES_DATA, learning_styles
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
        app.logger.info(f"Successfully loaded and processed data from {file_path}")
    except FileNotFoundError:
        app.logger.error(f"ERROR: '{file_path}' not found. Application will run with no assessment data.")
        LEARNING_STYLES_DATA = []
        learning_styles = {}
    except json.JSONDecodeError:
        app.logger.error(f"ERROR: Failed to decode '{file_path}'. Check syntax. Application will run with no assessment data.")
        LEARNING_STYLES_DATA = []
        learning_styles = {}
    except Exception as e:
        app.logger.error(f"An unexpected error occurred during JSON loading or processing from {file_path}: {e}")
        LEARNING_STYLES_DATA = []
        learning_styles = {}

# Load data on application startup
load_and_transform_data()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/assessment')
def assessment():
    questions = []
    question_number = 1
    
    for style, data in learning_styles.items():
        for question in data["questions"]:
            questions.append({
                "number": question_number,
                "text": question,
                "style": style
            })
            question_number += 1
    
    return render_template('assessment.html', questions=questions)

@app.route('/results', methods=['POST'])
def results():
    if request.method == 'POST':
        try:
            if not learning_styles: # Check if learning_styles data failed to load
                app.logger.error("Attempted to calculate results with no learning styles data loaded.")
                return "Error: Assessment data is unavailable. Please contact the administrator.", 500

            scores = {}
            for style_name in learning_styles:
                scores[style_name] = 0
            
            has_scores = False
            for key, value in request.form.items():
                if key.startswith('question_') and not key.endswith('_style'):
                    # key is like "question_1", "question_2", etc.
                    score = int(value) # Potential ValueError
                    has_scores = True
                    
                    # Retrieve the style associated with this question
                    style_for_question = request.form.get(f"{key}_style")
                    
                    if style_for_question and style_for_question in scores:
                        scores[style_for_question] += score
                    else:
                        # Log if a style submitted from form is not in our learning_styles keys
                        app.logger.warning(f"Received style '{style_for_question}' for question '{key}' which is not a recognized learning style.")
            
            if not has_scores and learning_styles : # No scores submitted, but styles exist
                 app.logger.info("No scores were submitted in the form.")
                 # It might be better to redirect to assessment or show a message
                 # For now, it will proceed and likely show 0 for all scores.

            # Find highest scoring styles
            # Handle case where scores might be empty if no questions were processed or all scores are 0
            if not scores: # Should not happen if learning_styles is populated
                 app.logger.error("Scores dictionary is empty before calculating max_score.")
                 return "Error: Could not calculate scores. No learning styles defined.", 500
            
            if not any(scores.values()): # All scores are zero
                max_score = 0 # Avoid ValueError on max() of empty sequence if all scores were 0 and filtered out
            else:
                max_score = max(scores.values())

            primary_styles = [style for style, score in scores.items() if score == max_score and max_score > 0] # Ensure max_score > 0 for a style to be primary
            
            # Get recommendations for primary styles
            recommendations = {}
            for style in primary_styles:
                recommendations[style] = learning_styles[style]["recommendations"]

            # Store results in session for download
            session['assessment_results'] = {
                'scores': scores,
                'primary_styles': primary_styles,
                'recommendations': recommendations,
                'learning_styles_data': learning_styles 
            }
            
            return render_template('results.html', scores=scores, primary_styles=primary_styles, 
                                   recommendations=recommendations, learning_styles=learning_styles)
        
        except ValueError as e:
            app.logger.error(f"ValueError during results processing: {e}. Form data: {request.form}")
            return "An error occurred while processing your results due to invalid data. Please try again.", 400
        except Exception as e:
            app.logger.error(f"Unexpected error during results processing: {e}")
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
