/**
 * Progress Bar Management
 * Controls the multi-step form progression
 */

let progressStep = 1;
const totalSteps = 5;

/**
 * Updates the progress bar based on current step
 * @param {number} currentStep - The current step in the process
 * @param {number} totalSteps - Total number of steps
 */
function updateProgressBar(currentStep, totalSteps) {
  // Update the progress line
  const progressPercent = ((currentStep - 1) / (totalSteps - 1)) * 100;
  document.querySelector('.progress-line').style.width = `${progressPercent}%`;

  // Update all step elements
  document.querySelectorAll('.progress-step').forEach((step, index) => {
    const stepNum = index + 1;
    if (stepNum < currentStep) {
      step.classList.add('completed');
      step.classList.remove('active');
    } else if (stepNum === currentStep) {
      step.classList.add('active');
      step.classList.remove('completed');
    } else {
      step.classList.remove('active', 'completed');
    }
  });
}

/**
 * Advances to a specific step if the current step is lower
 * @param {number} targetStep - The step to advance to
 */
function advanceToStep(targetStep) {
  if (progressStep < targetStep) {
    progressStep = targetStep;
    updateProgressBar(progressStep, totalSteps);
  }
}

/**
 * Initialize the progress bar
 */
function initProgressBar() {
  updateProgressBar(progressStep, totalSteps);
}

export default {
  updateProgressBar,
  advanceToStep,
  initProgressBar,
  getProgressStep: () => progressStep,
  setProgressStep: (step) => {
    progressStep = step;
    updateProgressBar(progressStep, totalSteps);
  }
};
