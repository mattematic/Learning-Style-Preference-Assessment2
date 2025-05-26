import os
import unittest
import json
from unittest.mock import patch, mock_open

# Add the parent directory to sys.path to allow importing 'main'
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the Flask app object and the data loading function from main.py
from main import app as flask_app, load_and_transform_data

# Global test data
MOCK_VALID_JSON_CONTENT = [
    {
        "style_name": "Visual",
        "questions": ["Q1V", "Q2V"],
        "recommendations": ["R1V", "R2V"],
        "category": "Sensory",
        "description": "Learns by seeing."
    },
    {
        "style_name": "Auditory",
        "questions": ["Q1A", "Q2A"],
        "recommendations": ["R1A", "R2A"],
        "category": "Sensory",
        "description": "Learns by hearing."
    },
    {
        "style_name": "Kinesthetic", # Added for more comprehensive tests
        "questions": ["Q1K", "Q2K"],
        "recommendations": ["R1K"],
        "category": "Physical",
        "description": "Learns by doing."
    }
]

MOCK_TRANSFORMED_STYLES = {
    item['style_name']: {
        "questions": item["questions"],
        "recommendations": item["recommendations"],
        "category": item["category"],
        "description": item["description"]
    } for item in MOCK_VALID_JSON_CONTENT
}


class TestMainApp(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Set up test client once for the class."""
        flask_app.config['TESTING'] = True
        flask_app.config['SECRET_KEY'] = 'test_secret_key' # For session testing
        # Disable CSRF protection if it's enabled and interferes with POST tests without a CSRF token
        flask_app.config['WTF_CSRF_ENABLED'] = False 
        cls.client = flask_app.test_client()

    def setUp(self):
        """Set up before each test."""
        # Ensure a clean state for learning_styles and LEARNING_STYLES_DATA before each test
        # by calling load_and_transform_data with a known good mock or clearing them.
        # This is crucial because these are global variables in main.py.
        # We will patch 'main.learning_styles' and 'main.LEARNING_STYLES_DATA' directly in tests
        # or use load_and_transform_data with mocks for data loading tests.
        pass


    def tearDown(self):
        """Clean up after each test."""
        with self.client.session_transaction() as sess:
            sess.clear()

    # --- Tests for learning_data.json Loading (using load_and_transform_data) ---

    @patch('main.open', new_callable=mock_open, read_data=json.dumps(MOCK_VALID_JSON_CONTENT))
    @patch('main.json.load') # Mock json.load to ensure it uses the mock_open's data
    @patch('main.app.logger') # Mock logger to check if it's called
    def test_load_valid_json(self, mock_logger, mock_json_load, mock_file_open):
        mock_json_load.return_value = MOCK_VALID_JSON_CONTENT # Configure mock_json_load
        
        load_and_transform_data() # Call the refactored load function
        
        # Access the global variables from the main module after loading
        from main import learning_styles, LEARNING_STYLES_DATA
        
        self.assertEqual(LEARNING_STYLES_DATA, MOCK_VALID_JSON_CONTENT)
        self.assertIn("Visual", learning_styles)
        self.assertEqual(learning_styles["Visual"]["category"], "Sensory")
        self.assertEqual(len(learning_styles), 3)
        mock_logger.info.assert_called_with("Successfully loaded and processed data from learning_data.json")

    @patch('main.open', side_effect=FileNotFoundError("File not found"))
    @patch('main.app.logger')
    def test_load_json_file_not_found(self, mock_logger, mock_file_open):
        load_and_transform_data()
        from main import learning_styles, LEARNING_STYLES_DATA
        self.assertEqual(learning_styles, {})
        self.assertEqual(LEARNING_STYLES_DATA, [])
        mock_logger.error.assert_called_with("ERROR: 'learning_data.json' not found. Application will run with no assessment data.")

    @patch('main.open', new_callable=mock_open, read_data="this is not json")
    @patch('main.json.load', side_effect=json.JSONDecodeError("err", "doc", 0))
    @patch('main.app.logger')
    def test_load_json_malformed(self, mock_logger, mock_json_load, mock_file_open):
        load_and_transform_data()
        from main import learning_styles, LEARNING_STYLES_DATA
        self.assertEqual(learning_styles, {})
        self.assertEqual(LEARNING_STYLES_DATA, [])
        mock_logger.error.assert_called_with("ERROR: Failed to decode 'learning_data.json'. Check syntax. Application will run with no assessment data.")

    # --- Test /assessment Route ---
    def test_assessment_route_get(self):
        # Patch main.learning_styles for this test to ensure it has known data
        with patch('main.learning_styles', MOCK_TRANSFORMED_STYLES):
            response = self.client.get('/assessment')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Learning Style Preference Assessment", response.data)
            # Check for question text from our mock data
            self.assertIn(b"Q1V", response.data) # Visual question
            self.assertIn(b"Q2A", response.data) # Auditory question
            self.assertIn(b"Kinesthetic", response.data) # Style name heading

    def test_assessment_route_no_data(self):
        # Test how assessment page behaves if learning_styles is empty
        with patch('main.learning_styles', {}):
            response = self.client.get('/assessment')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Learning Style Preference Assessment", response.data)
            # Should ideally show a message or no questions
            self.assertNotIn(b"Q1V", response.data) # No questions should be rendered

    # --- Test /results Route (Score Calculation) ---
    def test_results_route_single_primary_style(self):
        mock_form_data = {
            'question_1': '5', 'question_1_style': 'Visual',    # V: 5
            'question_2': '4', 'question_2_style': 'Visual',    # V: 4 (Total V: 9)
            'question_3': '1', 'question_3_style': 'Auditory',  # A: 1
            'question_4': '2', 'question_4_style': 'Auditory',  # A: 2 (Total A: 3)
            'question_5': '3', 'question_5_style': 'Kinesthetic',# K: 3 (Total K: 3)
        }
        with patch('main.learning_styles', MOCK_TRANSFORMED_STYLES):
            response = self.client.post('/results', data=mock_form_data)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Your Learning Style Results", response.data)
            
            with self.client.session_transaction() as sess:
                self.assertIn('assessment_results', sess)
                results = sess['assessment_results']
                self.assertEqual(results['scores']['Visual'], 9)
                self.assertEqual(results['scores']['Auditory'], 3)
                self.assertEqual(results['scores']['Kinesthetic'], 3)
                self.assertEqual(results['primary_styles'], ['Visual'])
                self.assertIn('Visual', results['recommendations'])
                self.assertEqual(results['recommendations']['Visual'], ["R1V", "R2V"])
                self.assertNotIn('Auditory', results['recommendations'])

    def test_results_route_multiple_primary_styles(self):
        mock_form_data = {
            'question_1': '5', 'question_1_style': 'Visual',       # V: 5
            'question_2': '3', 'question_2_style': 'Visual',       # V: 3 (Total V: 8)
            'question_3': '4', 'question_3_style': 'Auditory',     # A: 4
            'question_4': '4', 'question_4_style': 'Auditory',     # A: 4 (Total A: 8)
            'question_5': '1', 'question_5_style': 'Kinesthetic',  # K: 1 (Total K: 1)
        }
        with patch('main.learning_styles', MOCK_TRANSFORMED_STYLES):
            response = self.client.post('/results', data=mock_form_data)
            self.assertEqual(response.status_code, 200)
            with self.client.session_transaction() as sess:
                results = sess['assessment_results']
                self.assertEqual(results['scores']['Visual'], 8)
                self.assertEqual(results['scores']['Auditory'], 8)
                self.assertEqual(results['scores']['Kinesthetic'], 1)
                self.assertCountEqual(results['primary_styles'], ['Visual', 'Auditory'])
                self.assertIn('Visual', results['recommendations'])
                self.assertIn('Auditory', results['recommendations'])
                self.assertEqual(results['recommendations']['Visual'], ["R1V", "R2V"])
                self.assertEqual(results['recommendations']['Auditory'], ["R1A", "R2A"])

    def test_results_route_no_answers_submitted(self):
        # Test with empty form data but with styles loaded
        with patch('main.learning_styles', MOCK_TRANSFORMED_STYLES):
            response = self.client.post('/results', data={})
            self.assertEqual(response.status_code, 200) # Should still render results page
            with self.client.session_transaction() as sess:
                results = sess['assessment_results']
                self.assertEqual(results['scores']['Visual'], 0)
                self.assertEqual(results['scores']['Auditory'], 0)
                self.assertEqual(results['scores']['Kinesthetic'], 0)
                self.assertEqual(results['primary_styles'], []) # No primary style if all scores are 0
                self.assertEqual(results['recommendations'], {})


    def test_results_route_invalid_form_data_value_error(self):
        mock_form_data = {'question_1': 'not_a_number', 'question_1_style': 'Visual'}
        with patch('main.learning_styles', MOCK_TRANSFORMED_STYLES):
            response = self.client.post('/results', data=mock_form_data)
            self.assertEqual(response.status_code, 400) # Bad request
            self.assertIn(b"An error occurred while processing your results due to invalid data.", response.data)

    def test_results_route_no_learning_data_loaded(self):
        with patch('main.learning_styles', {}): # Simulate data loading failure
            response = self.client.post('/results', data={'question_1': '5', 'question_1_style': 'Visual'})
            self.assertEqual(response.status_code, 500)
            self.assertIn(b"Error: Assessment data is unavailable.", response.data)


    # --- Test /download_results Route ---
    def test_download_results_success(self):
        # 1. Populate session by calling /results
        mock_form_data = {
            'question_1': '5', 'question_1_style': 'Visual',
            'question_2': '2', 'question_2_style': 'Auditory',
        }
        with patch('main.learning_styles', MOCK_TRANSFORMED_STYLES):
            self.client.post('/results', data=mock_form_data) # Populates session

            # 2. Now test download
            response = self.client.get('/download_results')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, 'text/plain')
            self.assertIn('attachment;filename=learning_style_results.txt', response.headers['Content-Disposition'])
            
            # Check content (basic checks)
            content = response.data.decode('utf-8')
            self.assertIn("Learning Style Assessment Results", content)
            self.assertIn("Primary Learning Style(s):", content)
            self.assertIn("Visual: Learns by seeing.", content) # Primary style
            self.assertIn("All Scores:", content)
            self.assertIn("Visual (Sensory): 5/25", content) # Score for Visual
            self.assertIn("Auditory (Sensory): 2/25", content) # Score for Auditory
            self.assertIn("Kinesthetic (Physical): 0/25", content) # Score for Kinesthetic
            self.assertIn("For Visual Learners:", content) # Recommendations for primary
            self.assertIn("- R1V", content)
            self.assertNotIn("For Auditory Learners:", content) # Auditory not primary

    def test_download_results_no_session_data(self):
        response = self.client.get('/download_results') # No session data
        self.assertEqual(response.status_code, 302) # Redirect
        self.assertTrue(response.headers['Location'].endswith(('/'))) # Redirects to index

    def test_download_results_session_data_incomplete(self):
        # Simulate session data that's missing 'learning_styles_data' which is checked
        with self.client.session_transaction() as sess:
            sess['assessment_results'] = {
                'scores': {'Visual': 5},
                'primary_styles': ['Visual'],
                'recommendations': {'Visual': ['R1V']}
                # 'learning_styles_data' is missing
            }
        response = self.client.get('/download_results')
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"Error: Could not retrieve complete results data for download.", response.data)


if __name__ == '__main__':
    # Important: load_and_transform_data() in main.py will run with actual learning_data.json
    # when this test module is imported if not careful.
    # Tests for data loading should mock file operations globally if possible,
    # or ensure that load_and_transform_data can be called with a specific mock file path.
    # For this setup, we are calling load_and_transform_data() within test methods with mocks.
    unittest.main()
