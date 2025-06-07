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

export default {
  initExistingStudentData
};
