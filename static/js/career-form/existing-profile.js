/**
 * This module handles pre-filling the career form with existing student data
 */

// Function to initialize existing student data
function initExistingStudentData() {
  // Check if existing skills data is available
  const existingSkillsElement = document.getElementById('existing_skills');
  if (existingSkillsElement && existingSkillsElement.value) {
    try {
      // Parse existing skills data
      const skills = JSON.parse(existingSkillsElement.value);
      
      // Pre-populate the skills data input
      const skillsDataElement = document.getElementById('skills_data');
      if (skillsDataElement) {
        skillsDataElement.value = existingSkillsElement.value;
      }
      
      // Mark skills as selected when skills accordion is ready
      document.addEventListener('skillsAccordionReady', () => {
        preSelectExistingSkills(skills);
      });
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
  if (!Array.isArray(skills) || skills.length === 0) return;
  
  // Find all checkboxes in the skills accordion
  const skillCheckboxes = document.querySelectorAll('#skillsAccordion input[type="checkbox"]');
  
  skillCheckboxes.forEach(checkbox => {
    const skillName = checkbox.value.trim();
    if (skills.includes(skillName)) {
      checkbox.checked = true;
    }
  });
}

export default {
  initExistingStudentData
};
