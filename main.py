
from flask import Flask, render_template, request, redirect, url_for
import os
import json

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY') or os.urandom(24)

# Learning style categories and questions
learning_styles = {
    "Visual": {
        "questions": [
            "I prefer to see information written down.",
            "I easily remember faces but forget names.",
            "I use color-coding to organize information.",
            "Diagrams and charts help me understand complex ideas.",
            "I can easily visualize objects, plans, and outcomes in my mind."
        ],
        "recommendations": [
            "Mind mapping - Create visual diagrams connecting related concepts",
            "Color-coding - Use different colors for notes, categories, and important points",
            "Flashcards - Create visual study aids with diagrams or symbols",
            "Visualization - Picture concepts in your mind before tests",
            "Graphic organizers - Use charts, timelines, and diagrams to organize information"
        ]
    },
    "Auditory": {
        "questions": [
            "I prefer verbal instructions over written ones.",
            "I enjoy discussing ideas and concepts with others.",
            "I remember information better when I say it aloud.",
            "Background sounds or music help me concentrate.",
            "I find it easier to follow a spoken lecture than reading material."
        ],
        "recommendations": [
            "Recorded lectures - Record and replay important information",
            "Study groups - Discuss concepts verbally with peers",
            "Self-explanation - Teach concepts aloud to yourself or others",
            "Audio resources - Use audiobooks and podcasts",
            "Verbal repetition - Recite important information aloud"
        ]
    },
    "Reading/Writing": {
        "questions": [
            "I take detailed notes when learning something new.",
            "I prefer to read about a concept rather than have someone explain it.",
            "I organize my thoughts by writing them down.",
            "I enjoy creating written lists, outlines, and summaries.",
            "I prefer text-based learning materials over videos or demonstrations."
        ],
        "recommendations": [
            "Detailed notes - Rewrite notes in your own words",
            "Outlines - Create hierarchical structures of information",
            "Written summaries - Condense key points after studying",
            "Text-heavy resources - Seek out articles and books on topics",
            "Writing practice - Create sample questions and answers"
        ]
    },
    "Kinesthetic": {
        "questions": [
            "I prefer hands-on activities over lectures.",
            "I tend to use gestures and hand movements when speaking.",
            "I become restless during long periods of inactivity.",
            "I learn best when I can physically practice a skill.",
            "I prefer to try things out rather than read instructions."
        ],
        "recommendations": [
            "Hands-on experiments - Create physical models or demonstrations",
            "Movement while studying - Walk or move while reviewing material",
            "Role-playing - Act out scenarios or processes",
            "Real-world application - Find practical ways to apply concepts",
            "Study breaks - Take short, active breaks between study sessions"
        ]
    },
    "Deep Learning": {
        "questions": [
            "I seek to understand the underlying principles behind what I'm learning.",
            "I naturally look for connections between different subjects.",
            "I question assumptions and look for evidence before accepting ideas.",
            "I enjoy exploring complex problems and concepts.",
            "I prefer open-ended questions over memorization tasks."
        ],
        "recommendations": [
            "Concept mapping - Create diagrams showing relationships between ideas",
            "Socratic questioning - Ask probing questions about the material",
            "Interdisciplinary connections - Link new information to other subjects",
            "Case studies - Examine real-world examples of theoretical concepts",
            "Teaching others - Explain concepts to deepen your understanding"
        ]
    },
    "Strategic Learning": {
        "questions": [
            "I adapt my study approach based on what's being assessed.",
            "I'm good at managing my time and prioritizing tasks.",
            "I focus more energy on content that will be evaluated.",
            "I plan my approach before starting a learning task.",
            "I set clear goals for what I want to accomplish when studying."
        ],
        "recommendations": [
            "Practice tests - Create and take sample assessments",
            "Time management tools - Break studying into scheduled sessions",
            "Prioritization - Focus on high-value content first",
            "Goal-setting - Establish clear learning objectives",
            "Self-assessment - Regularly evaluate your understanding"
        ]
    }
}

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
        scores = {}
        for style in learning_styles:
            scores[style] = 0
        
        for key, value in request.form.items():
            if key.startswith('question_'):
                question_number = int(key.split('_')[1])
                score = int(value)
                
                # Find which style this question belongs to
                style_index = (question_number - 1) // 5
                style = list(learning_styles.keys())[style_index]
                
                scores[style] += score
        
        # Find highest scoring styles
        max_score = max(scores.values())
        primary_styles = [style for style, score in scores.items() if score == max_score]
        
        # Get recommendations for primary styles
        recommendations = {}
        for style in primary_styles:
            recommendations[style] = learning_styles[style]["recommendations"]
        
        return render_template('results.html', scores=scores, primary_styles=primary_styles, 
                               recommendations=recommendations, learning_styles=learning_styles)

if __name__ == '__main__':
    # Make sure templates directory exists
    os.makedirs('templates', exist_ok=True)
    
    # Create static directory for CSS
    os.makedirs('static', exist_ok=True)
    
    # Start the app
    app.run(host='0.0.0.0', port=8080)
