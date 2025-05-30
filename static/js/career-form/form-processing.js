/**
 * Form submission and processing
 * Handles form population, validation, and submission
 */
import progressBar from './progress-bar.js';
import { showToast, getCsrfToken } from './utils.js';

/**
 * Populate form with extracted data
 * @param {Object} studentInfo - Extracted student information
 * @param {Array} courses - Extracted courses
 */
function populateForm(studentInfo, courses) {
  // Populate form fields without animation
  ['student_id', 'id_number', 'fullname', 'last_name', 'birth_date', 'faculty', 'program', 'gpa'].forEach((field) => {
    const element = document.getElementById(field);
    if (element) {
      element.value = studentInfo[field] || '';

      // Mark as valid
      element.classList.add('is-valid');
      element.parentNode.classList.add('was-validated');
    }
  });

  const coursesDataElement = document.getElementById('courses_data');
  if (coursesDataElement) {
    coursesDataElement.value = JSON.stringify(courses);
  }

  // Display courses table without delay and animation
  displayCoursesTable(courses);

  // Scroll to the courses section
  const coursesContainer = document.getElementById('courses-container');
  if (coursesContainer) {
    coursesContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

/**
 * Display courses table
 * @param {Array} courses - The courses to display
 */
function displayCoursesTable(courses) {
  const coursesContainer = document.getElementById('courses-container');
  if (!coursesContainer) return;
  
  const hiddenInput = document.getElementById('courses_data');

  coursesContainer.innerHTML = '';
  coursesContainer.appendChild(hiddenInput);

  // Remove any existing alert
  const existingAlert = coursesContainer.closest('.card-body').querySelector('.alert');
  if (existingAlert) {
    existingAlert.remove();
  }

  // Create a header with summary stats
  const courseStats = document.createElement('div');
  courseStats.className = 'd-flex justify-content-between align-items-center mb-3';

  // Create table with improved styling
  const tableContainer = document.createElement('div');
  tableContainer.className = 'table-container table-responsive border rounded overflow-auto';
  tableContainer.style.maxHeight = '300px';
  tableContainer.style.boxShadow = '0 0 10px rgba(0,0,0,0.05)';

  const table = document.createElement('table');
  table.className = 'table table-hover mb-0';

  // Define grade colors
  const getGradeColor = (grade) => {
    if (grade === 'AA') return 'success';
    if (grade === 'BA' || grade === 'BB') return 'primary';
    if (grade === 'CB' || grade === 'CC') return 'info';
    if (grade === 'DC' || grade === 'DD') return 'warning';
    if (grade === 'FF') return 'danger';
    return 'secondary'; // For '--' or any other undefined grade
  };

  table.innerHTML = `
    <thead class="position-sticky top-0 bg-light">
      <tr>
        <th class="col-2">Code</th>
        <th class="col-8">Name</th>
        <th class="col-2 text-center">Grade</th>
      </tr>
    </thead>
    <tbody>
      ${courses.map(course => `
        <tr class="course-row">
          <td class="fw-bold">${course.code}</td>
          <td>${course.name}</td>
          <td class="text-center">
            <span class="badge bg-${getGradeColor(course.grade)} rounded-pill px-3 py-2">
              ${course.grade}
            </span>
          </td>
        </tr>
      `).join('')}
    </tbody>
  `;

  tableContainer.appendChild(table);
  coursesContainer.appendChild(courseStats);
  coursesContainer.appendChild(tableContainer);

  // Progress step update after displaying courses
  progressBar.advanceToStep(4);
}

/**
 * Initialize the form submission
 */
function initFormSubmission() {
  const form = document.getElementById('applicationForm');
  if (!form) return;

  // Make populateForm available globally for file upload module
  window.populateForm = populateForm;
  
  // Form submission with animated progress
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Update skills data before submission
    const updateSkillsDataFn = window.updateSkillsData;
    if (typeof updateSkillsDataFn === 'function') {
      updateSkillsDataFn();
    }

    // Show loading spinner
    document.getElementById('loadingSpinner').style.display = 'block';
    document.getElementById('submitBtn').disabled = true;

    // Animate the progress bar
    const progressBar = document.querySelector('#loadingSpinner .progress-bar');
    progressBar.style.transition = 'width 2s ease';

    setTimeout(() => {
      progressBar.style.width = '30%';

      setTimeout(() => {
        progressBar.style.width = '60%';

        setTimeout(() => {
          progressBar.style.width = '90%';
        }, 800);
      }, 700);
    }, 300);

    try {
      const formData = new FormData(e.target);

      // Get the CSRF token
      const csrftoken = getCsrfToken();

      const response = await fetch('/api/submit-application/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrftoken
        },
        body: formData
      });

      if (response.ok) {
        const result = await response.json();
        console.log('Submission result:', result);

        if (result.data && result.data.job_recommendations) {
          // Store recommendations in session storage
          sessionStorage.setItem('jobRecommendations', JSON.stringify(result.data.job_recommendations));

          // Redirect to the recommendations page
          window.location.href = '/recommendation-results/';
        } else {
          alert('No job recommendations were found. Please check your input data.');
          document.getElementById('loadingSpinner').style.display = 'none';
          document.getElementById('submitBtn').disabled = false;
        }
      } else {
        const errorText = await response.text();
        showToast('Failed to submit application: ' + errorText, 'error');
        document.getElementById('loadingSpinner').style.display = 'none';
        document.getElementById('submitBtn').disabled = false;
      }
    } catch (error) {
      // Hide loading spinner on error
      document.getElementById('loadingSpinner').style.display = 'none';
      document.getElementById('submitBtn').disabled = false;
      console.error('Error submitting form:', error);
      showToast('An error occurred while submitting your application. Please try again.', 'error');
    }
  });
}

export default {
  populateForm,
  displayCoursesTable,
  initFormSubmission
};
