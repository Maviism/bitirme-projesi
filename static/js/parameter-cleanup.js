/**
 * Parameter cleanup utility for resume generator
 * Helps ensure that URL parameters are properly formatted
 */

// Clean up URL parameters when the page loads
document.addEventListener('DOMContentLoaded', function() {
    // Function to clean and validate job_id parameter
    function cleanJobIdParameter() {
        const jobIdField = document.querySelector('input[name="job_id"]');
        if (!jobIdField) return; // No job ID field found
        
        const jobId = jobIdField.value;
        if (!jobId) return; // No job ID value
        
        // Clean the job ID (remove any non-numeric characters)
        const cleanedJobId = jobId.toString().replace(/[^0-9]/g, '');
        
        if (cleanedJobId !== jobId) {
            console.log(`Cleaned job ID from ${jobId} to ${cleanedJobId}`);
            jobIdField.value = cleanedJobId;
        }
        
        console.log('Using job ID:', cleanedJobId);
    }
    
    // Run the cleanup
    cleanJobIdParameter();
    
    // Debug info for troubleshooting
    console.log('Resume form parameters:');
    document.querySelectorAll('input[type="hidden"]').forEach(field => {
        console.log(`- ${field.name}: ${field.value}`);
    });
});
