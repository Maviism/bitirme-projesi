/**
 * File Upload Handler
 * Manages drag and drop functionality and PDF processing
 */
import progressBar from './progress-bar.js';
import { showToast } from './utils.js';

// PDF.js should be loaded in the main HTML
let pdfjsLib;

// DOM Elements
let uploadContainer;
let fileInput;

/**
 * Initialize the file upload functionality
 */
function initFileUpload() {
  uploadContainer = document.getElementById('uploadContainer');
  fileInput = document.getElementById('pdfInput');
  
  // Initialize PDF.js
  pdfjsLib = window.pdfjsLib;
  pdfjsLib.GlobalWorkerOptions.workerSrc = document.querySelector('script[data-pdf-worker-src]').getAttribute('data-pdf-worker-src');

  setupEventListeners();
}

/**
 * Set up the drag and drop event listeners
 */
function setupEventListeners() {
  // Handle drag events
  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    uploadContainer.addEventListener(eventName, preventDefaults, false);
  });

  // Highlight drop zone when file is dragged over it
  ['dragenter', 'dragover'].forEach(eventName => {
    uploadContainer.addEventListener(eventName, highlight, false);
  });

  ['dragleave', 'drop'].forEach(eventName => {
    uploadContainer.addEventListener(eventName, unhighlight, false);
  });

  // Handle dropped files
  uploadContainer.addEventListener('drop', handleDrop, false);

  // Handle file selection via the file input
  fileInput.addEventListener('change', function (e) {
    if (this.files.length > 0) {
      handleFileSelection(this.files[0]);
    }
  });

  // Add click event to the browse button
  const browseButton = uploadContainer.querySelector('button');
  if (browseButton) {
    browseButton.addEventListener('click', () => {
      fileInput.click();
    });
  }
}

/**
 * Prevent default behaviors for drag and drop
 */
function preventDefaults(e) {
  e.preventDefault();
  e.stopPropagation();
}

/**
 * Highlight the drop zone
 */
function highlight() {
  uploadContainer.classList.add('drag-over');
}

/**
 * Remove highlight from the drop zone
 */
function unhighlight() {
  uploadContainer.classList.remove('drag-over');
}

/**
 * Handle dropped files
 */
function handleDrop(e) {
  const dt = e.dataTransfer;
  const files = dt.files;

  if (files.length > 0 && files[0].type === 'application/pdf') {
    fileInput.files = files;
    handleFileSelection(files[0]);
  } else {
    showToast('Please upload a PDF file', 'error');
  }
}

/**
 * Process the selected file
 */
function handleFileSelection(file) {
  // Show loading effect on the upload container
  uploadContainer.classList.add('uploading');
  uploadContainer.innerHTML = `
    <div class="text-center">
      <div class="spinner-border text-primary mb-3" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
      <h4>Analyzing your transcript...</h4>
      <p>Please wait while we extract your academic information</p>
    </div>
  `;

  // Process the file
  extractPdfText(file)
    .then(text => {
      const studentInfo = extractStudentInfo(text);
      const courses = extractCourses(text);
      
      // Call the form population function (from another module)
      window.populateForm(studentInfo, courses);

      // Update upload container with success message
      uploadContainer.classList.remove('uploading');
      uploadContainer.classList.add('success');
      uploadContainer.innerHTML = `
        <div class="text-center">
          <div class="text-success mb-3">
            <i class="fas fa-check-circle fa-4x"></i>
          </div>
          <h4>Transcript Processed Successfully!</h4>
          <p class="text-muted">We've extracted your student information and academic courses. Continue filling out the form below.</p>
        </div>
      `;

      // Move to next step in progress bar
      progressBar.setProgressStep(2);

      // Scroll to student info & courses section
      const combinedSection = Array.from(document.querySelectorAll('h3.h5')).find(
        h3 => h3.textContent.includes('Student Information & Academic Courses')
      )?.closest('.form-card');

      if (combinedSection) {
        combinedSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }

      // Show animated toast notification
      showToast('Transcript processed successfully!', 'success');
    })
    .catch(error => {
      console.error("Error extracting PDF text:", error);

      // Update upload container with error message
      uploadContainer.classList.remove('uploading');
      uploadContainer.classList.add('error');
      uploadContainer.innerHTML = `
        <div class="text-center">
          <div class="text-danger mb-3">
            <i class="fas fa-exclamation-triangle fa-4x"></i>
          </div>
          <h4>Error Processing Transcript</h4>
          <p>We couldn't process your PDF file. Please try again with a different file.</p>
          <button class="btn btn-custom btn-primary mt-3" type="button" id="retryUpload">
            <i class="fas fa-redo me-2"></i>Try Again
          </button>
        </div>
      `;

      // Add event listener to retry button
      document.getElementById('retryUpload').addEventListener('click', resetUploadContainer);

      // Show animated toast notification
      showToast('Error processing transcript', 'error');
    });
}

/**
 * Reset upload container to initial state
 */
function resetUploadContainer() {
  uploadContainer.classList.remove('uploading', 'success', 'error');
  uploadContainer.innerHTML = `
    <div class="upload-icon">
      <i class="fas fa-cloud-upload-alt"></i>
    </div>
    <h3 class="upload-text">Drag & Drop your PDF transcript here</h3>
    <p>or</p>
    <button class="btn btn-custom btn-primary" type="button">Browse Files</button>
    <input type="file" id="pdfInput" class="file-input" accept="application/pdf">
  `;

  // Re-attach event listeners
  setupEventListeners();
}

/**
 * PDF extraction and text cleaning function
 */
async function extractPdfText(file) {
  return new Promise((resolve, reject) => {
    const fileReader = new FileReader();
    fileReader.onload = async function () {
      try {
        const typedarray = new Uint8Array(this.result);
        const loadingTask = pdfjsLib.getDocument(typedarray);

        // Add progress tracking
        loadingTask.onProgress = function (progress) {
          const percent = progress.loaded / progress.total * 100;
          console.log(`Loading PDF: ${Math.round(percent)}%`);
        };

        const pdf = await loadingTask.promise;
        const textChunks = [];

        for (let i = 1; i <= pdf.numPages; i++) {
          const page = await pdf.getPage(i);
          const content = await page.getTextContent({ normalizeWhitespace: true, disableCombineTextItems: false });
          textChunks.push(processPageContent(content));
        }

        const text = textChunks.join("\n");
        const cleanedText = text.replace(/\s+/g, ' ')
          .replace(/(\w+)\s+:\s+/g, '$1: ')
          .replace(/(\d)\s+(\d)/g, '$1$2')
          .replace(/(\d{2})\s+\/\s+(\d{2})\s+\/\s+(\d{4})/g, '$1/$2/$3')
          .replace(/([A-Z]{3})\s+(\d{4})/g, '$1$2');
        resolve(cleanedText);
      } catch (error) {
        reject(error);
      }
    };
    fileReader.onerror = reject;
    fileReader.readAsArrayBuffer(file);
  });
}

/**
 * PDF page content processing function
 */
function processPageContent(content) {
  const items = content.items.map(item => ({
    text: item.str,
    x: Math.round(item.transform[4]),
    y: Math.round(item.transform[5]),
    width: Math.round(item.width) || 0
  }));

  const yPositions = {};
  items.forEach(item => {
    const yPos = Math.floor(item.y / 3) * 3;
    if (!yPositions[yPos]) yPositions[yPos] = [];
    yPositions[yPos].push(item);
  });

  const sortedYPositions = Object.keys(yPositions).map(Number).sort((a, b) => b - a);

  return sortedYPositions.map(yPos => {
    let line = '';
    let lastX = -9999;
    yPositions[yPos].sort((a, b) => a.x - b.x).forEach(item => {
      if (item.x - lastX > 10 && line !== '') line += ' ';
      line += item.text;
      lastX = item.x + item.width;
    });
    return line;
  }).join('\n');
}

/**
 * Student info extraction
 */
function extractStudentInfo(text) {
  const patterns = {
    student_id: /Öğrenci No\s*\(Student ID\)\s*:\s*([0-9]+)/,
    id_number: /T\.C\. Kimlik No\s*\(TR Identity No\)\s*:\s*([0-9]+)/,
    fullname: /Adı\s*\(Given Name\)\s*:\s*([A-ZİĞÜŞÖÇ\s]+?)(?=\s+Soyadı|\s*$)/i,
    last_name: /Soyadı\s*\(Surname\)\s*:\s*([A-ZİĞÜŞÖÇ\s]+?)(?=\s+Doğum|\s*$)/i,
    birth_date: /Doğum Tarihi\s*\(Date of Birth\)\s*:\s*([0-9/]+)/,
    faculty: /Eğitim Birimi(?:.*?):\s*([^:\r\n]+?)(?=\s*:[0-9]|\s*\()/,
    program: /Programı\/ABD\/ASD(?:.*?):\s*([^:\r\n]+?)(?=\s*:|$)/,
    gpa: /Genel Not Ortalaması(?:.*?):\s*([0-9.]+)/
  };

  return Object.entries(patterns).reduce((info, [key, pattern]) => {
    const match = text.match(pattern);
    info[key] = match ? match[1].trim() : "Not Found";
    return info;
  }, {});
}

/**
 * Course list extraction
 */
function extractCourses(text) {
  const courses = [];
  const courseRegex = /([A-Z]{3}\d{4}[İ]?)\s+(.*?)\s+([ZS])\s+Tr\s+(\d+)\s+(\d+)\s+(\d+\s+)?([\w-]{1,2})\s+([\d.-]+|\-\-)\s+([A-Za-z]{1,3})?/g;

  let match;
  while ((match = courseRegex.exec(text)) !== null) {
    courses.push({
      code: match[1],
      name: match[2].trim().replace(/\s*\([^)]*\)\s*$/, ''),
      grade: match[7] || "--"
    });
  }

  if (courses.length === 0) {
    const altCourseRegex = /([A-Z]{3}\d{4}[İ]?)\s+(.*?)\s+([ZS])\s+Tr\s+(\d+)\s+(\d+)/g;
    while ((match = altCourseRegex.exec(text)) !== null) {
      courses.push({
        code: match[1],
        name: match[2].trim().replace(/\s*\([^)]*\)\s*$/, ''),
        grade: "--"
      });
    }
  }

  return courses;
}

export default {
  initFileUpload,
  resetUploadContainer
};
