document.addEventListener('DOMContentLoaded', function() {
    // Create enhanced mobile menu button
    const menuButton = document.createElement('button');
    menuButton.className = 'mobile-menu-toggle';
    menuButton.innerHTML = `
        <div class="menu-icon">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;
    menuButton.style.cssText = `
        position: fixed;
        top: 1rem;
        left: 1rem;
        z-index: 1000;
        background: linear-gradient(135deg, #667eea, #764ba2);
        border: none;
        color: white;
        cursor: pointer;
        padding: 0.75rem;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(102, 126, 234, 0.3);
        display: none;
        transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        width: 50px;
        height: 50px;
    `;

    // Add menu icon animation styles
    const menuIconStyles = document.createElement('style');
    menuIconStyles.textContent = `
        .menu-icon {
            width: 24px;
            height: 18px;
            position: relative;
            transform: rotate(0deg);
            transition: 0.5s ease-in-out;
        }
        
        .menu-icon span {
            display: block;
            position: absolute;
            height: 3px;
            width: 100%;
            background: white;
            border-radius: 2px;
            opacity: 1;
            left: 0;
            transform: rotate(0deg);
            transition: 0.25s ease-in-out;
        }
        
        .menu-icon span:nth-child(1) {
            top: 0px;
        }
        
        .menu-icon span:nth-child(2) {
            top: 7px;
        }
        
        .menu-icon span:nth-child(3) {
            top: 14px;
        }
        
        .mobile-menu-toggle.active .menu-icon span:nth-child(1) {
            top: 7px;
            transform: rotate(135deg);
        }
        
        .mobile-menu-toggle.active .menu-icon span:nth-child(2) {
            opacity: 0;
            left: -60px;
        }
        
        .mobile-menu-toggle.active .menu-icon span:nth-child(3) {
            top: 7px;
            transform: rotate(-135deg);
        }
        
        .mobile-menu-toggle:hover {
            transform: scale(1.1);
            box-shadow: 0 6px 25px rgba(102, 126, 234, 0.4);
        }
        
        .mobile-menu-toggle:active {
            transform: scale(0.95);
        }
        
        .sidebar-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            z-index: 999;
            opacity: 0;
            visibility: hidden;
            transition: all 0.3s ease;
            backdrop-filter: blur(5px);
        }
        
        .sidebar-overlay.show {
            opacity: 1;
            visibility: visible;
        }
        
        .sidebar {
            transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            z-index: 1001;
        }
        
        .sidebar.show {
            transform: translateX(0) !important;
        }
        
        @media (max-width: 768px) {
            .sidebar {
                transform: translateX(-100%);
            }
            
            .main-content {
                margin-left: 0 !important;
                transition: margin-left 0.3s ease;
            }
            
            .header {
                margin-left: 0 !important;
                transition: margin-left 0.3s ease;
            }
        }
        
        @media (max-width: 480px) {
            .mobile-menu-toggle {
                top: 0.5rem;
                left: 0.5rem;
                width: 45px;
                height: 45px;
                padding: 0.5rem;
            }
            
            .menu-icon {
                width: 20px;
                height: 15px;
            }
        }
    `;
    document.head.appendChild(menuIconStyles);

    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    const header = document.querySelector('.header');
    
    // Create overlay for closing sidebar
    const overlay = document.createElement('div');
    overlay.className = 'sidebar-overlay';
    document.body.appendChild(overlay);
    document.body.appendChild(menuButton);

    function toggleMenu() {
        const isOpen = sidebar.classList.contains('show');
        
        if (isOpen) {
            closeSidebar();
        } else {
            openSidebar();
        }
    }
    
    function openSidebar() {
        sidebar.classList.add('show');
        overlay.classList.add('show');
        menuButton.classList.add('active');
        document.body.style.overflow = 'hidden';
        
        // Add haptic feedback on mobile
        if ('vibrate' in navigator) {
            navigator.vibrate(50);
        }
    }
    
    function closeSidebar() {
        sidebar.classList.remove('show');
        overlay.classList.remove('show');
        menuButton.classList.remove('active');
        document.body.style.overflow = '';
    }

    menuButton.addEventListener('click', toggleMenu);
    overlay.addEventListener('click', closeSidebar);
    
    // Close sidebar when clicking on nav links (mobile)
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', function() {
            if (window.innerWidth <= 768) {
                closeSidebar();
            }
        });
    });
    
    // Enhanced keyboard navigation
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && sidebar.classList.contains('show')) {
            closeSidebar();
        }
        
        // Ctrl + M to toggle menu
        if (e.ctrlKey && e.key === 'm') {
            e.preventDefault();
            toggleMenu();
        }
    });

    // Show menu button on mobile and handle responsive behavior
    function handleResponsive() {
        if (window.innerWidth <= 768) {
            menuButton.style.display = 'block';
            // Ensure sidebar is closed on mobile
            if (!sidebar.classList.contains('show')) {
                sidebar.style.transform = 'translateX(-100%)';
            }
        } else {
            menuButton.style.display = 'none';
            closeSidebar();
            // Reset sidebar position on desktop
            sidebar.style.transform = '';
            sidebar.classList.remove('show');
        }
    }

    // Initial setup
    handleResponsive();

    // Handle resize with debouncing
    let resizeTimeout;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(handleResponsive, 250);
    });
    
    // Handle touch gestures for swipe to open/close
    let touchStartX = 0;
    let touchEndX = 0;
    
    document.addEventListener('touchstart', function(e) {
        touchStartX = e.changedTouches[0].screenX;
    });
    
    document.addEventListener('touchend', function(e) {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
    });
    
    function handleSwipe() {
        if (window.innerWidth > 768) return;
        
        const swipeThreshold = 50;
        const diff = touchStartX - touchEndX;
        
        // Swipe right to open, left to close
        if (Math.abs(diff) > swipeThreshold) {
            if (diff < 0 && !sidebar.classList.contains('show') && touchStartX < 50) {
                openSidebar();
            } else if (diff > 0 && sidebar.classList.contains('show')) {
                closeSidebar();
            }
        }
    }
    
    // Add smooth scroll behavior for better UX
    document.documentElement.style.scrollBehavior = 'smooth';
});