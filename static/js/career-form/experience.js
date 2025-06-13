/**
 * Experience section management
 * Handles the experience input cards functionality
 */
import progressBar from './progress-bar.js';

/**
 * Experience input template
 * @param {string} type - 'organization' or 'internship'
 * @param {number} index - The index of this experience entry
 * @returns {string} - HTML template for the experience input card
 */
const createExperienceInput = (type, index) => {
  const isOrg = type === 'organization';
  const prefix = isOrg ? 'org' : 'intern';
  const nameField = 'institution_name'; // Use unified field name
  const nameLabel = isOrg ? 'Organization Name' : 'Company Name';
  const icon = isOrg ? 'fa-users' : 'fa-building';
  const color = isOrg ? 'primary' : 'info';

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
            <input type="text" id="${prefix}_${nameField}_${index}" name="${type}s[${index}][${nameField}]" class="form-control" required placeholder="${nameLabel}">
            <input type="hidden" name="${type}s[${index}][experience_type]" value="${type}">
            <label for="${prefix}_${nameField}_${index}">
              <i class="fas ${isOrg ? 'fa-sitemap' : 'fa-building'} me-2"></i>${nameLabel}
            </label>
          </div>
        </div>
        <div class="col-md-6">
          <div class="mb-3 form-floating">
            <input type="text" id="${prefix}_position_${index}" name="${type}s[${index}][position]" class="form-control" required placeholder="Your position">
            <label for="${prefix}_position_${index}">
              <i class="fas fa-user-tie me-2"></i>Position
            </label>
          </div>
        </div>
      </div>
      
      <div class="row">
        <div class="col-md-6">
          <div class="mb-3 form-floating">
            <input type="date" id="${prefix}_start_date_${index}" name="${type}s[${index}][start_date]" class="form-control" required placeholder="Start Date">
            <label for="${prefix}_start_date_${index}">
              <i class="fas fa-calendar-day me-2"></i>Start Date
            </label>
          </div>
        </div>
        <div class="col-md-6">
          <div class="mb-3 form-floating">
            <input type="date" id="${prefix}_end_date_${index}" name="${type}s[${index}][end_date]" class="form-control" placeholder="End Date">
            <label for="${prefix}_end_date_${index}">
              <i class="fas fa-calendar-check me-2"></i>End Date (leave empty if current)
            </label>
          </div>
        </div>
      </div>
      
      <div class="mb-3 form-floating">
        <textarea id="${prefix}_description_${index}" name="${type}s[${index}][description]" class="form-control" placeholder="Description of your role"></textarea>
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
};

/**
 * Add experience input with animation
 * @param {string} type - 'organization' or 'internship'
 */
function addExperienceInput(type) {
  const container = document.getElementById(`${type}-inputs`);
  const inputGroup = document.createElement('div');
  inputGroup.innerHTML = createExperienceInput(type, container.children.length);

  // Add to container
  container.appendChild(inputGroup.firstElementChild);

  // Focus on the first input field
  const firstInput = inputGroup.querySelector('input');
  if (firstInput) {
    setTimeout(() => {
      firstInput.focus();
    }, 300); // Give time for animation to start
  }

  // Update progress step after adding experience
  progressBar.advanceToStep(5);
}

/**
 * Remove input with animation
 * @param {HTMLElement} button - The remove button that was clicked
 * @param {string} type - 'organization' or 'internship'
 */
function removeExperienceInput(button, type) {
  const card = button.closest('.form-card');

  // Add removal animation class
  card.style.opacity = '0';
  card.style.transform = 'translateY(-10px)';
  card.style.transition = 'all 0.3s ease';

  // After animation completes, remove the element
  setTimeout(() => {
    const container = card.parentNode;
    container.removeChild(card);

    // Update indices for remaining cards
    Array.from(container.querySelectorAll('.form-card')).forEach((card, index) => {
      // Update the badge number
      const badge = card.querySelector('.badge');
      if (badge) badge.textContent = `#${index + 1}`;

      // Update form field names
      Array.from(card.querySelectorAll('[name]')).forEach(input => {
        const nameAttr = input.getAttribute('name');
        if (nameAttr) {
          input.setAttribute('name', nameAttr.replace(/\[\d+\]/, `[${index}]`));
        }
      });
    });
  }, 300);
}

/**
 * Initialize the experience section
 */
function initExperienceSection() {
  // Add global reference to removeExperienceInput function
  window.removeExperienceInput = removeExperienceInput;
  
  // Add experience buttons with animations
  document.getElementById('add-organization').addEventListener('click', () => {
    addExperienceInput('organization');
    // Switch to the organization tab if not already active
    const orgTab = document.getElementById('organization-tab');
    bootstrap.Tab.getOrCreateInstance(orgTab).show();
  });

  document.getElementById('add-internship').addEventListener('click', () => {
    addExperienceInput('internship');
    // Switch to the internship tab if not already active
    const internTab = document.getElementById('internship-tab');
    bootstrap.Tab.getOrCreateInstance(internTab).show();
  });

  // Tab events to update progress steps
  document.querySelectorAll('#experienceTabs .nav-link').forEach(tab => {
    tab.addEventListener('shown.bs.tab', () => {
      progressBar.advanceToStep(4);
    });
  });
}

export default {
  initExperienceSection,
  addExperienceInput
};
