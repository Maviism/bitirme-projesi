/**
 * Utility functions for the career form
 */

/**
 * Display a toast notification
 * @param {string} message - The message to display
 * @param {string} type - 'success' or 'error'
 */
export function showToast(message, type) {
  // Check if a toast container already exists, create if not
  let toastContainer = document.querySelector('.toast-container');
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
    toastContainer.style.zIndex = '1080';
    document.body.appendChild(toastContainer);
  }
  
  // Create unique ID for this toast
  const toastId = 'toast-' + Date.now();
  
  // Create toast HTML using Bootstrap's structure
  const toastHtml = `
    <div id="${toastId}" class="toast bg-${type === 'success' ? 'success' : 'danger'} text-white" role="alert" aria-live="assertive" aria-atomic="true">
      <div class="toast-body d-flex align-items-center">
        <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'} me-2"></i>
        ${message}
        <button type="button" class="btn-close btn-close-white ms-auto" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
    </div>
  `;
  
  // Add toast to container
  toastContainer.insertAdjacentHTML('beforeend', toastHtml);
  
  // Get the toast element and create Bootstrap Toast instance
  const toastEl = document.getElementById(toastId);
  const toast = new bootstrap.Toast(toastEl, {
    autohide: true,
    delay: 3000
  });
  
  // Show the toast
  toast.show();
  
  // Remove the toast element after it's hidden
  toastEl.addEventListener('hidden.bs.toast', function() {
    this.remove();
  });
}

/**
 * Utility function to get CSRF token from cookie
 * @returns {string} - The CSRF token
 */
export function getCsrfToken() {
  let cookieValue = null;
  const name = 'csrftoken';
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

/**
 * Add scroll animations for a more dynamic feel
 */
export function setupScrollAnimations() {
  const animateOnScroll = () => {
    const elements = document.querySelectorAll('.form-card');
    
    elements.forEach(element => {
      const position = element.getBoundingClientRect();
      
      // Check if element is in viewport
      if (position.top < window.innerHeight && position.bottom >= 0) {
        if (!element.classList.contains('has-animated')) {
          element.classList.add('animate-fade-in', 'has-animated');
        }
      }
    });
  };
  
  // Add smooth scrolling and animations
  window.addEventListener('scroll', animateOnScroll);
  
  // Trigger initial animation
  setTimeout(() => {
    animateOnScroll();
  }, 300);
}

/**
 * Setup form field interactions
 */
export function setupFormFieldInteractions() {
  document.querySelectorAll('.form-control').forEach(field => {
    field.addEventListener('focus', function () {
      this.closest('.mb-3').classList.add('highlight-field');
    });
    
    field.addEventListener('blur', function () {
      this.closest('.mb-3').classList.remove('highlight-field');
      
      // Simple validation feedback
      if (this.value.trim() !== '' && this.hasAttribute('required')) {
        this.classList.add('is-valid');
        this.classList.remove('is-invalid');
      } else if (this.hasAttribute('required')) {
        this.classList.add('is-invalid');
        this.classList.remove('is-valid');
      }
    });
  });
}
