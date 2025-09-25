/**
 * Main JavaScript file for Exam Generator Application
 */

document.addEventListener('DOMContentLoaded', function() {
    // Enable Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Enable Bootstrap popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Confirm before canceling an exam
    const cancelButtons = document.querySelectorAll('.cancel-exam-btn');
    cancelButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to cancel this exam? All progress will be lost.')) {
                e.preventDefault();
            }
        });
    });

    // Confirm before submitting an exam
    const examForm = document.getElementById('exam-form');
    if (examForm) {
        examForm.addEventListener('submit', function(e) {
            // Count answered questions
            const inputs = examForm.querySelectorAll('input[type="radio"]:checked, input[type="text"]');
            const answeredCount = Array.from(inputs).filter(input => input.value.trim() !== '').length;
            
            // Get total questions
            const questionCards = document.querySelectorAll('.question-card');
            const totalQuestions = questionCards.length;
            
            // If less than 50% answered, confirm submission
            if (answeredCount < totalQuestions / 2) {
                if (!confirm(`You've only answered ${answeredCount} out of ${totalQuestions} questions. Are you sure you want to submit?`)) {
                    e.preventDefault();
                }
            }
        });
    }

    // Auto-save answers for online exam (every 30 seconds)
    const autosaveEl = document.getElementById('autosave-status');
    const saveAnswers = function() {
        if (!examForm) return;
        
        const formData = new FormData(examForm);
        const answers = {};
        
        for (const [key, value] of formData.entries()) {
            answers[key] = value;
        }
        
        localStorage.setItem('examAnswers', JSON.stringify(answers));
        const ts = new Date().toLocaleTimeString();
        if (autosaveEl) {
            autosaveEl.textContent = `Saved at ${ts}`;
            autosaveEl.classList.remove('text-muted');
            autosaveEl.classList.add('text-success');
        }
        console.log('Answers auto-saved at', ts);
    };
    
    // Load saved answers if available
    const loadSavedAnswers = function() {
        if (!examForm) return;
        
        const savedAnswers = localStorage.getItem('examAnswers');
        if (!savedAnswers) return;
        
        try {
            const answers = JSON.parse(savedAnswers);
            
            for (const [questionId, answer] of Object.entries(answers)) {
                // For radio buttons
                const radio = examForm.querySelector(`input[type="radio"][name="${questionId}"][value="${answer}"]`);
                if (radio) {
                    radio.checked = true;
                    continue;
                }
                
                // For text inputs
                const textInput = examForm.querySelector(`input[type="text"][name="${questionId}"]`);
                if (textInput) {
                    textInput.value = answer;
                }
            }
            
            if (autosaveEl) {
                autosaveEl.textContent = 'Restored saved answers';
                autosaveEl.classList.add('text-info');
            }
            console.log('Saved answers loaded');
        } catch (e) {
            console.error('Error loading saved answers:', e);
        }
    };
    
    // Set up auto-save timer
    if (examForm) {
        loadSavedAnswers();
        setInterval(saveAnswers, 30000); // Save every 30 seconds
        
        // Save on change
        examForm.addEventListener('input', function() {
            if (autosaveEl) {
                autosaveEl.textContent = 'Saving...';
                autosaveEl.classList.remove('text-success','text-info');
                autosaveEl.classList.add('text-muted');
            }
            saveAnswers();
        });
        
        // Clear saved answers when form is submitted
        examForm.addEventListener('submit', function() {
            localStorage.removeItem('examAnswers');
        });
    }
    
    // Highlight current page in navigation
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
});