/**
 * This module handles pre-filling the career form with existing student data
 */

// Function to initialize existing student data
function initExistingStudentData() {

  // Check for existing courses data
  const coursesJsonScript = document.getElementById('courses-json');
  if (coursesJsonScript) {
    try {
      // Parse courses data
      const courses = JSON.parse(coursesJsonScript.textContent);
      // Pre-populate the courses data input
      const coursesDataElement = document.getElementById('courses_data');
      if (coursesDataElement) {
        coursesDataElement.value = JSON.stringify(courses);
      }
      
      // Import form processing to display courses table
      import('./form-processing.js').then(module => {
        if (module.default && module.default.displayCoursesTable) {
          // Display courses table
          module.default.displayCoursesTable(courses);
        }
      });
    } catch (error) {
      console.error('Error parsing existing courses data:', error);
    }
  }
  

  // Check if existing skills data is available
  const existingSkillsScript = document.getElementById('existing-skills-json');
  if (existingSkillsScript && existingSkillsScript.textContent) {
    try {
      // Parse existing skills data from JSON script
      const skills = JSON.parse(existingSkillsScript.textContent);
      
      // Pre-populate the skills data input
      const skillsDataElement = document.getElementById('skills_data');
      if (skillsDataElement) {
        skillsDataElement.value = JSON.stringify(skills);
      }
      
      // Mark skills as selected when skills accordion is ready
      // First, check if the accordion is already ready
      const existingAccordion = document.getElementById('skillsAccordion');
      if (existingAccordion && existingAccordion.children.length > 0) {
        setTimeout(() => {
          preSelectExistingSkills(skills);
        }, 100);
      } else {
        document.addEventListener('skillsAccordionReady', () => {
          // Small delay to ensure all DOM elements are ready
          setTimeout(() => {
            preSelectExistingSkills(skills);
          }, 100);
        });
      }
    } catch (error) {
      console.error('Error parsing existing skills:', error);
    }
  }
  
  // Check for existing organizations data
  const organizationsJsonScript = document.getElementById('existing-organizations-json');
  if (organizationsJsonScript) {
    try {
      const organizations = JSON.parse(organizationsJsonScript.textContent);
      if (organizations.length > 0) {
        displayExistingExperiences('organization', organizations);
      }
    } catch (error) {
      console.error('Error parsing existing organizations data:', error);
    }
  }

  // Check for existing internships data
  const internshipsJsonScript = document.getElementById('existing-internships-json');
  if (internshipsJsonScript) {
    try {
      const internships = JSON.parse(internshipsJsonScript.textContent);
      if (internships.length > 0) {
        displayExistingExperiences('internship', internships);
      }
    } catch (error) {
      console.error('Error parsing existing internships data:', error);
    }
  }
  
  // If form has existing data, advance the progress bar
  if (document.querySelector('.alert-info') && document.getElementById('fullname').value) {
    // Import progressBar dynamically
    import('./progress-bar.js').then(module => {
      if (module.default && module.default.advanceToStep) {
        // Skip to step 2 or 3 since student data is already populated
        module.default.advanceToStep(3);
      }
    });
  }
}

// Function to pre-select existing skills in the UI
function preSelectExistingSkills(skills) {
  if (!Array.isArray(skills) || skills.length === 0) {
    return;
  }
  
  // Find all checkboxes in the skills accordion
  const skillCheckboxes = document.querySelectorAll('#skillsAccordion .skill-input');
  
  skillCheckboxes.forEach(checkbox => {
    const skillName = checkbox.value.trim();
    
    if (skills.includes(skillName)) {
      checkbox.checked = true;
      
      // Trigger the change event to update UI components (badges, counts, etc.)
      const changeEvent = new Event('change', { bubbles: true });
      checkbox.dispatchEvent(changeEvent);
    }
  });
  
  // Update the skills data hidden field after pre-selection
  if (typeof window.updateSkillsData === 'function') {
    window.updateSkillsData();
  }
}

// Function to display existing experience data
function displayExistingExperiences(type, experiences) {
  if (!Array.isArray(experiences) || experiences.length === 0) {
    return;
  }

  // Import the experience module to get access to createExperienceInput
  import('./experience.js').then(module => {
    const container = document.getElementById(`${type}-inputs`);
    
    experiences.forEach((experience, index) => {
      // Create the experience input HTML
      const experienceHTML = createExperienceInputWithData(type, index, experience);
      
      // Create a temporary div to hold the HTML
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = experienceHTML;
      
      // Add to container
      container.appendChild(tempDiv.firstElementChild);
    });
  });
}

// Function to create experience input template with existing data
function createExperienceInputWithData(type, index, data) {
  const isOrg = type === 'organization';
  const prefix = isOrg ? 'org' : 'intern';
  const nameField = 'institution_name';
  const nameLabel = isOrg ? 'Organization Name' : 'Company Name';
  const icon = isOrg ? 'fa-users' : 'fa-building';
  const color = isOrg ? 'primary' : 'info';

  // Format dates for display
  const startDate = data.start_date || '';
  const endDate = data.end_date || '';

  return `
  <div class="form-card mb-3 animate-fade-in position-relative">
    <div class="card-body">
      <div class="text-${color} mb-3">
        <i class="fas ${icon} fa-2x"></i>
        <span class="badge bg-light text-dark position-absolute top-0 end-0 m-2" style="z-index: 10;">#${index + 1}</span>
      </div>
      
      <div class="row">
        <div class="col-md-6">
          <div class="mb-3 form-floating">
            <input type="text" id="${prefix}_${nameField}_${index}" name="${type}s[${index}][${nameField}]" class="form-control" required placeholder="${nameLabel}" value="${data.institution_name || ''}">
            <input type="hidden" name="${type}s[${index}][experience_type]" value="${type}">
            <label for="${prefix}_${nameField}_${index}">
              <i class="fas ${isOrg ? 'fa-sitemap' : 'fa-building'} me-2"></i>${nameLabel}
            </label>
          </div>
        </div>
        <div class="col-md-6">
          <div class="mb-3 form-floating">
            <input type="text" id="${prefix}_position_${index}" name="${type}s[${index}][position]" class="form-control" required placeholder="Your position" value="${data.position || ''}">
            <label for="${prefix}_position_${index}">
              <i class="fas fa-user-tie me-2"></i>Position
            </label>
          </div>
        </div>
      </div>
      
      <div class="row">
        <div class="col-md-6">
          <div class="mb-3 form-floating">
            <input type="date" id="${prefix}_start_date_${index}" name="${type}s[${index}][start_date]" class="form-control" required placeholder="Start Date" value="${startDate}">
            <label for="${prefix}_start_date_${index}">
              <i class="fas fa-calendar-day me-2"></i>Start Date
            </label>
          </div>
        </div>
        <div class="col-md-6">
          <div class="mb-3 form-floating">
            <input type="date" id="${prefix}_end_date_${index}" name="${type}s[${index}][end_date]" class="form-control" placeholder="End Date" value="${endDate}">
            <label for="${prefix}_end_date_${index}">
              <i class="fas fa-calendar-check me-2"></i>End Date (leave empty if current)
            </label>
          </div>
        </div>
      </div>
      
      <div class="mb-3 form-floating">
        <textarea id="${prefix}_description_${index}" name="${type}s[${index}][description]" class="form-control" placeholder="Description of your role">${data.description || ''}</textarea>
        <label for="${prefix}_description_${index}">
          <i class="fas fa-align-left me-2"></i>Description
        </label>
      </div>
      
      <div class="text-end">
        <button type="button" class="btn btn-custom btn-danger" onclick="removeExperienceInput(this, '${type}')">
          <i class="fas fa-trash-alt me-2"></i>Remove
        </button>
      </div>
    </div>
  </div>
  `;
}

export default {
  initExistingStudentData
};
