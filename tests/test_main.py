import os
import unittest
import json
from unittest.mock import patch, mock_open

# Add the parent directory to sys.path to allow importing 'main'
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the Flask app object and the data loading function from main.py
from main import app as flask_app, load_and_transform_data, ALL_QUESTIONS as main_ALL_QUESTIONS, learning_styles as main_learning_styles

# Global test data
MOCK_JSON_CONTENT_FOR_TESTS = [
    {
        "style_name": "Visual",
        "questions": ["Q1V (Visual Question 1)", "Q2V (Visual Question 2)"],
        "recommendations": ["R1V", "R2V"],
        "category": "Sensory",
        "description": "Learns by seeing."
    },
    {
        "style_name": "Auditory",
        "questions": ["Q1A (Auditory Question 1)"],
        "recommendations": ["R1A", "R2A"],
        "category": "Sensory",
        "description": "Learns by hearing."
    },
    {
        "style_name": "Kinesthetic",
        "questions": ["Q1K (Kinesthetic Question 1)"],
        "recommendations": ["R1K"],
        "category": "Physical",
        "description": "Learns by doing."
    }
] # Total 2+1+1 = 4 questions

MOCK_ALL_QUESTIONS_LIST = [
    {'id': 1, 'text': 'Q1V (Visual Question 1)', 'style': 'Visual'},
    {'id': 2, 'text': 'Q2V (Visual Question 2)', 'style': 'Visual'},
    {'id': 3, 'text': 'Q1A (Auditory Question 1)', 'style': 'Auditory'},
    {'id': 4, 'text': 'Q1K (Kinesthetic Question 1)', 'style': 'Kinesthetic'},
]

MOCK_LEARNING_STYLES_DICT = {
    item['style_name']: {
        "questions": item["questions"],
        "recommendations": item["recommendations"],
        "category": item["category"],
        "description": item["description"]
    } for item in MOCK_JSON_CONTENT_FOR_TESTS
}


class TestMainAppPaginated(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        flask_app.config['TESTING'] = True
        flask_app.config['SECRET_KEY'] = 'test_secret_key_paginated'
        flask_app.config['WTF_CSRF_ENABLED'] = False
        cls.client = flask_app.test_client()

    def setUp(self):
        # Patch the global variables in main.py for each test
        # This ensures that each test runs with a known, consistent set of questions and styles
        self.all_questions_patcher = patch('main.ALL_QUESTIONS', MOCK_ALL_QUESTIONS_LIST)
        self.learning_styles_patcher = patch('main.learning_styles', MOCK_LEARNING_STYLES_DICT)
        
        self.mock_all_questions = self.all_questions_patcher.start()
        self.mock_learning_styles = self.learning_styles_patcher.start()

        # Clear session before each test
        with self.client.session_transaction() as sess:
            sess.clear()

    def tearDown(self):
        self.all_questions_patcher.stop()
        self.learning_styles_patcher.stop()
        # Session is cleared in setUp for the next test

    # --- Data Loading Tests (Remain similar, but ensure they work with new structure if needed) ---
    @patch('main.open', new_callable=mock_open, read_data=json.dumps(MOCK_JSON_CONTENT_FOR_TESTS))
    @patch('main.json.load')
    @patch('main.app.logger')
    def test_load_valid_json_and_populates_all_questions(self, mock_logger, mock_json_load, mock_file_open):
        mock_json_load.return_value = MOCK_JSON_CONTENT_FOR_TESTS
        load_and_transform_data() # Call the refactored load function
        
        # Check global vars from main module after loading (they are re-imported or accessed via main module)
        self.assertEqual(main_learning_styles["Visual"]["category"], "Sensory")
        self.assertEqual(len(main_ALL_QUESTIONS), 4) # 2 Visual, 1 Auditory, 1 Kinesthetic
        self.assertEqual(main_ALL_QUESTIONS[0]['text'], "Q1V (Visual Question 1)")
        self.assertEqual(main_ALL_QUESTIONS[3]['style'], "Kinesthetic")
        mock_logger.info.assert_any_call(f"Successfully loaded and processed data from learning_data.json. {len(MOCK_JSON_CONTENT_FOR_TESTS[0]['questions'] + MOCK_JSON_CONTENT_FOR_TESTS[1]['questions'] + MOCK_JSON_CONTENT_FOR_TESTS[2]['questions'])} questions loaded.")


    # --- /assessment Route Tests (Paginated Flow) ---
    def test_assessment_start_initial_get(self):
        """Test GET /assessment - should redirect to question 1 and init session."""
        response = self.client.get('/assessment')
        self.assertEqual(response.status_code, 302) # Redirect
        self.assertTrue(response.headers['Location'].endswith('/assessment/1'))
        with self.client.session_transaction() as sess:
            self.assertIn('assessment_answers', sess)
            self.assertEqual(sess['assessment_answers'], {})

    def test_assessment_get_specific_question(self):
        """Test GET /assessment/<question_num> - valid question."""
        # Initialize session first
        self.client.get('/assessment') 
        response = self.client.get('/assessment/1')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Question 1 of 4", response.data)
        self.assertIn(MOCK_ALL_QUESTIONS_LIST[0]['text'].encode(), response.data)

    def test_assessment_get_question_out_of_bounds_too_high(self):
        self.client.get('/assessment') # Init session
        response = self.client.get('/assessment/99') # Question num too high
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers['Location'].endswith('/results')) # Redirects to results if out of bounds

    def test_assessment_get_question_out_of_bounds_zero(self):
        self.client.get('/assessment') # Init session
        response = self.client.get('/assessment/0')
        self.assertEqual(response.status_code, 302) # Redirects to results (or q1 if no answers)
        self.assertTrue(response.headers['Location'].endswith('/assessment/1'))


    def test_assessment_get_question_with_existing_answer(self):
        with self.client.session_transaction() as sess:
            sess['assessment_answers'] = {'1': {'score': 4, 'style': 'Visual'}}
        
        response = self.client.get('/assessment/1')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'value="4" required checked', response.data) # Check if score 4 is checked

    def test_assessment_post_answer_first_question(self):
        self.client.get('/assessment') # Initialize session
        response = self.client.post('/assessment/1', data={'score': '5'})
        self.assertEqual(response.status_code, 302) # Redirect to next question
        self.assertTrue(response.headers['Location'].endswith('/assessment/2'))
        with self.client.session_transaction() as sess:
            self.assertIn('1', sess['assessment_answers'])
            self.assertEqual(sess['assessment_answers']['1']['score'], 5)
            self.assertEqual(sess['assessment_answers']['1']['style'], MOCK_ALL_QUESTIONS_LIST[0]['style'])

    def test_assessment_post_answer_last_question(self):
        self.client.get('/assessment') # Initialize session
        # Simulate answering previous questions
        with self.client.session_transaction() as sess:
            sess['assessment_answers'] = {
                '1': {'score': 1, 'style': 'Visual'},
                '2': {'score': 2, 'style': 'Visual'},
                '3': {'score': 3, 'style': 'Auditory'},
            }
        
        response = self.client.post(f'/assessment/{len(MOCK_ALL_QUESTIONS_LIST)}', data={'score': '4'}) # Post to last q
        self.assertEqual(response.status_code, 302) # Redirect to results
        self.assertTrue(response.headers['Location'].endswith('/results'))
        with self.client.session_transaction() as sess:
            self.assertIn(str(len(MOCK_ALL_QUESTIONS_LIST)), sess['assessment_answers'])
            self.assertEqual(sess['assessment_answers'][str(len(MOCK_ALL_QUESTIONS_LIST))]['score'], 4)

    def test_assessment_post_invalid_score(self):
        self.client.get('/assessment') # Initialize session
        response = self.client.post('/assessment/1', data={'score': '99'}) # Invalid score
        self.assertEqual(response.status_code, 200) # Re-renders current page
        self.assertIn(b"Please select a valid score between 1 and 5.", response.data)
        self.assertIn(MOCK_ALL_QUESTIONS_LIST[0]['text'].encode(), response.data) # Still on Q1

    def test_assessment_previous_button_navigation(self):
        self.client.get('/assessment') # To q1
        self.client.post('/assessment/1', data={'score': '3'}) # To q2
        
        response = self.client.get('/assessment/2') # Current q is 2
        self.assertIn(b'<i class="material-icons left">chevron_left</i>Previous', response.data) # Check for previous button with Materialize icon
        
        # Manually go to previous via GET (simulating button click)
        response_prev = self.client.get('/assessment/1')
        self.assertEqual(response_prev.status_code, 200)
        self.assertIn(MOCK_ALL_QUESTIONS_LIST[0]['text'].encode(), response_prev.data)
        self.assertIn(b'value="3" required checked', response_prev.data) # Previously submitted answer for Q1

    # --- /results Route Tests (Paginated Flow) ---
    def test_results_calculation_from_session(self):
        # Simulate full assessment
        self.client.get('/assessment') # Init
        self.client.post('/assessment/1', data={'score': '5'}) # Q1 (Visual) -> 5
        self.client.post('/assessment/2', data={'score': '4'}) # Q2 (Visual) -> 4 (Total Visual: 9)
        self.client.post('/assessment/3', data={'score': '3'}) # Q3 (Auditory) -> 3
        self.client.post('/assessment/4', data={'score': '5'}) # Q4 (Kinesthetic) -> 5
        
        # Now GET /results
        response = self.client.get('/results')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Your Learning Style Results", response.data)

        with self.client.session_transaction() as sess:
            # Check that assessment_answers is cleared
            self.assertNotIn('assessment_answers', sess) 
            # Check that assessment_results (for download) is populated
            self.assertIn('assessment_results', sess)
            results_for_download = sess['assessment_results']
            
            self.assertEqual(results_for_download['scores']['Visual'], 9)
            self.assertEqual(results_for_download['scores']['Auditory'], 3)
            self.assertEqual(results_for_download['scores']['Kinesthetic'], 5)
            self.assertCountEqual(results_for_download['primary_styles'], ['Visual'])
            self.assertIn('Visual', results_for_download['recommendations'])

    def test_results_get_with_no_session_answers(self):
        response = self.client.get('/results')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers['Location'].endswith('/assessment')) # Redirect to start assessment

    # --- Edge Case: No Questions Loaded ---
    @patch('main.ALL_QUESTIONS', []) # Simulate no questions loaded
    @patch('main.learning_styles', {})
    def test_assessment_start_no_questions_loaded(self):
        response = self.client.get('/assessment')
        self.assertEqual(response.status_code, 200) # Renders assessment page with error
        self.assertIn(b"Assessment data is unavailable.", response.data)

    @patch('main.ALL_QUESTIONS', [])
    @patch('main.learning_styles', {})
    def test_results_no_questions_or_styles_loaded(self):
        # Simulate trying to go to results when no data was ever loaded
        # This might happen if user bookmarks /results and json fails to load
        with self.client.session_transaction() as sess:
            # Put some dummy answers, but learning_styles will be empty
            sess['assessment_answers'] = {'1': {'score': 5, 'style': 'NonExistentStyle'}}
        
        response = self.client.get('/results')
        self.assertEqual(response.status_code, 500) # Error because learning_styles is empty
        self.assertIn(b"Error: Assessment data is unavailable.", response.data)

    # --- Download Route (ensure setup reflects new flow) ---
    def test_download_results_after_paginated_assessment(self):
        # 1. Simulate full assessment to populate session correctly
        self.client.get('/assessment') # Init
        self.client.post('/assessment/1', data={'score': '5'}) # Visual
        self.client.post('/assessment/2', data={'score': '4'}) # Visual
        self.client.post('/assessment/3', data={'score': '2'}) # Auditory
        self.client.post('/assessment/4', data={'score': '1'}) # Kinesthetic
        
        # This POST to last question redirects to /results, which populates 'assessment_results'
        self.client.get('/results') # This call processes answers and sets 'assessment_results'

        # 2. Now test download
        response_download = self.client.get('/download_results')
        self.assertEqual(response_download.status_code, 200)
        self.assertEqual(response_download.mimetype, 'text/plain')
        content = response_download.data.decode('utf-8')
        self.assertIn("Visual: Learns by seeing.", content)
        self.assertIn("Visual (Sensory): 9/25", content) # 5+4
        self.assertIn("Auditory (Sensory): 2/25", content)
        self.assertIn("Kinesthetic (Physical): 1/25", content)


if __name__ == '__main__':
    unittest.main()
