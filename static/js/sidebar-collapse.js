document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    
    // Create collapse toggle button
    const collapseButton = document.createElement('button');
    collapseButton.className = 'sidebar-collapse-toggle';
    collapseButton.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M15 18l-6-6 6-6"/>
        </svg>
    `;
    
    // Add button to sidebar
    sidebar.insertBefore(collapseButton, sidebar.firstChild);
    
    // Toggle sidebar collapse
    collapseButton.addEventListener('click', function() {
        sidebar.classList.toggle('collapsed');
        mainContent.classList.toggle('expanded');
        collapseButton.classList.toggle('rotated');
    });
});