/**
 * Main JavaScript file for the career form
 * Integrates all modules and initializes the form
 */
import progressBar from './progress-bar.js';
import fileUpload from './file-upload.js';
import skills from './skills.js';
import experience from './experience.js';
import formProcessing from './form-processing.js';
import existingProfile from './existing-profile.js';
import { setupScrollAnimations, setupFormFieldInteractions } from './utils.js';

/**
 * Initialize the application
 */
document.addEventListener('DOMContentLoaded', function () {
  // Initialize progress bar
  progressBar.initProgressBar();
  
  // Initialize file upload
  fileUpload.initFileUpload();
  
  // Generate skills sections
  skills.generateSkillsSections();
  
  // Expose updateSkillsData globally for form submission
  window.updateSkillsData = skills.updateSkillsData;
  
  // Initialize experience section
  experience.initExperienceSection();
  
  // Initialize form submission
  formProcessing.initFormSubmission();
  
  // Initialize existing student data if available
  existingProfile.initExistingStudentData();
  
  // Setup animations and interactions
  setupScrollAnimations();
  setupFormFieldInteractions();
});
