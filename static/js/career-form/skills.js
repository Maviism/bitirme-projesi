/**
 * Skills management module
 * Handles skills section functionality
 */
import progressBar from './progress-bar.js';

const skillsData = {
  "Programming Languages": {
    isExpanded: true, // first category starts expanded
    skills: [
      { id: "skill_python", value: "Python", label: "Python" },
      { id: "skill_java", value: "Java", label: "Java" },
      { id: "skill_cpp", value: "C++", label: "C++" },
      { id: "skill_c", value: "C", label: "C" },
      { id: "skill_csharp", value: "C#", label: "C#" },
      { id: "skill_javascript", value: "JavaScript", label: "JavaScript" },
      { id: "skill_typescript", value: "TypeScript", label: "TypeScript" },
      { id: "skill_go", value: "Go", label: "Go" },
      { id: "skill_php", value: "PHP", label: "PHP" },
      { id: "skill_ruby", value: "Ruby", label: "Ruby" }
    ]
  },
  "Web Development": {
    isExpanded: false,
    skills: [
      { id: "skill_html", value: "HTML/CSS", label: "HTML/CSS" },
      { id: "skill_react", value: "React", label: "React" },
      { id: "skill_angular", value: "Angular", label: "Angular" },
      { id: "skill_vue", value: "Vue.js", label: "Vue.js" },
      { id: "skill_bootstrap", value: "Bootstrap", label: "Bootstrap" },
      { id: "skill_sass", value: "SASS/SCSS", label: "SASS/SCSS" },
      { id: "skill_node", value: "Node.js", label: "Node.js" },
      { id: "skill_express", value: "Express.js", label: "Express.js" },
      { id: "skill_django", value: "Django", label: "Django" },
      { id: "skill_flask", value: "Flask", label: "Flask" },
      { id: "skill_spring", value: "Spring", label: "Spring" },
      { id: "skill_api", value: "API Development", label: "API Development" },
      { id: "skill_graphql", value: "GraphQL", label: "GraphQL" }
    ]
  },
  "Databases": {
    isExpanded: false,
    skills: [
      { id: "skill_sql", value: "SQL", label: "SQL" },
      { id: "skill_mysql", value: "MySQL", label: "MySQL" },
      { id: "skill_postgresql", value: "PostgreSQL", label: "PostgreSQL" },
      { id: "skill_sql_server", value: "SQL Server", label: "SQL Server" },
      { id: "skill_oracle", value: "Oracle", label: "Oracle" },
      { id: "skill_mongodb", value: "MongoDB", label: "MongoDB" },
      { id: "skill_redis", value: "Redis", label: "Redis" },
      { id: "skill_elasticsearch", value: "Elasticsearch", label: "Elasticsearch" },
      { id: "skill_orm", value: "ORM Tools", label: "ORM Tools" }
    ]
  },
  "DevOps & Cloud": {
    isExpanded: false,
    skills: [
      { id: "skill_git", value: "Git", label: "Git" },
      { id: "skill_github", value: "GitHub", label: "GitHub" },
      { id: "skill_docker", value: "Docker", label: "Docker" },
      { id: "skill_kubernetes", value: "Kubernetes", label: "Kubernetes" },
      { id: "skill_ci_cd", value: "CI/CD", label: "CI/CD" },
      { id: "skill_aws", value: "AWS", label: "AWS" },
      { id: "skill_azure", value: "Azure", label: "Microsoft Azure" },
      { id: "skill_gcp", value: "GCP", label: "Google Cloud Platform" },
      { id: "skill_firebase", value: "Firebase", label: "Firebase" },
      { id: "skill_heroku", value: "Heroku", label: "Heroku" }
    ]
  },
  "Data Science & AI": {
    isExpanded: false,
    skills: [
      { id: "skill_pandas", value: "Pandas", label: "Pandas" },
      { id: "skill_numpy", value: "NumPy", label: "NumPy" },
      { id: "skill_jupyter", value: "Jupyter", label: "Jupyter" },
      { id: "skill_r", value: "R Language", label: "R Language" },
      { id: "skill_data_viz", value: "Data Visualization", label: "Data Visualization" },
      { id: "skill_scikit", value: "Scikit-Learn", label: "Scikit-Learn" },
      { id: "skill_tensorflow", value: "TensorFlow", label: "TensorFlow" },
      { id: "skill_pytorch", value: "PyTorch", label: "PyTorch" },
      { id: "skill_nlp", value: "NLP", label: "Natural Language Processing" },
      { id: "skill_computer_vision", value: "Computer Vision", label: "Computer Vision" },
      { id: "skill_machine_learning", value: "Machine Learning", label: "Machine Learning" }
    ]
  },
  "Other Skills": {
    isExpanded: false,
    skills: [
      { id: "skill_android", value: "Android", label: "Android" },
      { id: "skill_ios", value: "iOS/Swift", label: "iOS/Swift" },
      { id: "skill_flutter", value: "Flutter", label: "Flutter" },
      { id: "skill_react_native", value: "React Native", label: "React Native" },
      { id: "skill_oop", value: "Object-Oriented Programming", label: "Object-Oriented Programming" },
      { id: "skill_data_structures", value: "Data Structures", label: "Data Structures" },
      { id: "skill_algorithms", value: "Algorithms", label: "Algorithms" },
      { id: "skill_testing", value: "Software Testing", label: "Software Testing" },
      { id: "skill_agile", value: "Agile", label: "Agile" },
      { id: "skill_project_management", value: "Project Management", label: "Project Management" }
    ]
  }
};

/**
 * Generate the skills sections dynamically
 */
function generateSkillsSections() {
  const accordion = document.getElementById('skillsAccordion');

  // Clear accordion first
  accordion.innerHTML = '';

  // Generate content for each skill category
  Object.entries(skillsData).forEach(([category, data], categoryIndex) => {
    // Create unique ID for this category
    const headingId = `heading${category.replace(/\W+/g, '')}`;
    const collapseId = `collapse${category.replace(/\W+/g, '')}`;
    const isExpanded = data.isExpanded;

    // Get icon based on category
    const getCategoryIcon = (category) => {
      const icons = {
        'Programming Languages': 'fa-code',
        'Web Development': 'fa-globe',
        'Databases': 'fa-database',
        'DevOps & Cloud': 'fa-cloud',
        'Data Science & AI': 'fa-brain',
        'Other Skills': 'fa-tools'
      };
      return icons[category] || 'fa-star';
    };

    // Create accordion item
    const accordionItem = document.createElement('div');
    accordionItem.className = 'accordion-item';

    // Create header
    accordionItem.innerHTML = `
      <h2 class="accordion-header" id="${headingId}">
        <button class="accordion-button ${isExpanded ? '' : 'collapsed'}" type="button" 
                data-bs-toggle="collapse" data-bs-target="#${collapseId}" 
                aria-expanded="${isExpanded}" aria-controls="${collapseId}">
          <i class="fas ${getCategoryIcon(category)} me-2"></i> ${category}
          <span class="badge bg-primary ms-2 selected-count" id="badge-${headingId}">0</span>
        </button>
      </h2>
      <div id="${collapseId}" class="accordion-collapse collapse ${isExpanded ? 'show' : ''}" 
           aria-labelledby="${headingId}">
        <div class="accordion-body">
          <!-- Skills will be added here -->
        </div>
      </div>
    `;

    // Add to accordion
    accordion.appendChild(accordionItem);

    // Get body element to add skills to
    const accordionBody = accordionItem.querySelector('.accordion-body');

    // Create skills grid directly
    const skillsGrid = document.createElement('div');
    skillsGrid.className = 'skills-grid';

    // Add each skill to the grid
    data.skills.forEach(skill => {
      const skillDiv = document.createElement('div');
      skillDiv.className = 'skill-checkbox';

      skillDiv.innerHTML = `
        <label class="custom-checkbox" for="${skill.id}">
          <input type="checkbox" id="${skill.id}" class="skill-input" value="${skill.value}" data-heading="${headingId}">
          <span class="checkmark"></span>
          ${skill.label}
        </label>
      `;

      skillsGrid.appendChild(skillDiv);
    });

    // Add skills grid to accordion body
    accordionBody.appendChild(skillsGrid);
  });

  // Add event listeners to all generated checkboxes
  document.querySelectorAll('.skill-input').forEach(checkbox => {
    checkbox.addEventListener('change', function () {
      updateSkillsData();
      updateSkillCategoryCount(this);
    });
  });
}

/**
 * Update skill category count badges
 * @param {HTMLElement} checkbox - The checkbox that was changed
 */
function updateSkillCategoryCount(checkbox) {
  const headingId = checkbox.dataset.heading;
  const badge = document.getElementById(`badge-${headingId}`);
  const checkboxes = document.querySelectorAll(`input[data-heading="${headingId}"]:checked`);

  badge.textContent = checkboxes.length;

  if (checkboxes.length > 0) {
    badge.classList.remove('bg-light', 'text-dark');
    badge.classList.add('bg-primary');
  } else {
    badge.classList.remove('bg-primary');
    badge.classList.add('bg-light', 'text-dark');
  }

  // When a skill is checked, move to the next progress step
  if (checkbox.checked) {
    progressBar.advanceToStep(3);
  }
}

/**
 * Update the skills data hidden field
 */
function updateSkillsData() {
  const selectedSkills = Array.from(document.querySelectorAll('.skill-input:checked')).map(cb => cb.value);
  document.getElementById('skills_data').value = JSON.stringify(selectedSkills);
}

export default {
  generateSkillsSections,
  updateSkillsData
};
