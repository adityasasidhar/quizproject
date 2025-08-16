# Testing the Exam Generator Application

This document outlines the testing procedures for the Exam Generator application.

## Manual Testing Plan

### 1. Setup Testing

- [ ] Verify that the application installs correctly with all dependencies
- [ ] Confirm that the API key is properly loaded from apikey.txt
- [ ] Check that the application starts without errors

### 2. Online Exam Flow Testing

- [ ] Test the home page loads correctly
- [ ] Verify that clicking "Start Online Exam" navigates to the exam setup page
- [ ] Test all form fields in the exam setup page:
  - [ ] Exam Type dropdown (JEE Mains, JEE Advanced, NEET UG)
  - [ ] Difficulty Level dropdown (easy, medium, hard)
  - [ ] Exam Format dropdown (MCQ, subjective, mixed)
- [ ] Verify that clicking "Generate Exam" creates a new exam
- [ ] Check that the online exam page displays questions correctly
- [ ] Test answering questions:
  - [ ] MCQ selection
  - [ ] Text input for numerical/subjective questions
- [ ] Verify that the timer works correctly
- [ ] Test the auto-save functionality by:
  - [ ] Answering some questions
  - [ ] Refreshing the page
  - [ ] Confirming answers are still there
- [ ] Submit the exam and verify results page displays:
  - [ ] Overall score
  - [ ] Percentage
  - [ ] Feedback based on score
  - [ ] Individual question results
  - [ ] Correct answers

### 3. Offline Exam Flow Testing

- [ ] Test that clicking "Start Offline Exam" navigates to the exam setup page
- [ ] Verify that the offline mode is correctly identified
- [ ] Generate an exam for offline use
- [ ] Test downloading the exam paper
- [ ] Verify the JSON file contains all questions and answers
- [ ] Test the "Upload Answers" functionality:
  - [ ] Navigate to the upload page
  - [ ] Test drag-and-drop file upload
  - [ ] Test file selection via button
  - [ ] Verify image preview works
  - [ ] Submit an image with answers
- [ ] Verify that Gemini correctly processes the uploaded image
- [ ] Check that results are displayed correctly

### 4. Edge Case Testing

- [ ] Test with invalid API key
- [ ] Test with no internet connection
- [ ] Test with very large exam papers
- [ ] Test with unsupported file types for upload
- [ ] Test with poor quality images for answer upload
- [ ] Test submitting an exam with no answers
- [ ] Test browser back button behavior during exam
- [ ] Test session expiration handling

## Automated Testing (Future Implementation)

For future development, consider implementing automated tests:

1. **Unit Tests**:
   - Test individual functions in app.py
   - Test the generate_paper function
   - Test the image processing functionality

2. **Integration Tests**:
   - Test the full exam generation flow
   - Test the answer evaluation process

3. **End-to-End Tests**:
   - Simulate user interactions with Selenium
   - Test the complete online and offline exam flows

## Performance Testing

- [ ] Test application with multiple concurrent users
- [ ] Measure response time for exam generation
- [ ] Measure response time for image processing
- [ ] Test with various image sizes and qualities

## Security Testing

- [ ] Verify that API keys are properly secured
- [ ] Check for potential CSRF vulnerabilities
- [ ] Test input validation and sanitization
- [ ] Verify that user data is properly handled

## Browser Compatibility

- [ ] Test on Chrome
- [ ] Test on Firefox
- [ ] Test on Safari
- [ ] Test on Edge
- [ ] Test on mobile browsers

## Accessibility Testing

- [ ] Test keyboard navigation
- [ ] Test screen reader compatibility
- [ ] Verify color contrast meets WCAG standards
- [ ] Check for proper semantic HTML

## Known Issues and Limitations

- The application requires an internet connection for exam generation and answer evaluation
- Large images may take longer to process
- Handwriting recognition accuracy depends on image quality
- The application is not designed for high-concurrency usage