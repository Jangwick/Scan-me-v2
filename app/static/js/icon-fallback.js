/**
 * Icon Fallback System
 * Detects if Font Awesome loaded and provides alternatives
 */

class IconFallbackManager {
    constructor() {
        this.fontAwesomeLoaded = false;
        this.checkAttempts = 0;
        this.maxAttempts = 5;
        this.init();
    }

    init() {
        // Check multiple times as fonts might load slowly
        this.checkFontAwesome();
        
        // Recheck after short intervals
        setTimeout(() => this.checkFontAwesome(), 500);
        setTimeout(() => this.checkFontAwesome(), 1000);
        setTimeout(() => this.checkFontAwesome(), 2000);
    }

    checkFontAwesome() {
        this.checkAttempts++;
        
        // Create test element
        const testElement = document.createElement('i');
        testElement.className = 'fas fa-home';
        testElement.style.position = 'absolute';
        testElement.style.left = '-9999px';
        testElement.style.fontSize = '16px';
        document.body.appendChild(testElement);

        // Check computed styles
        setTimeout(() => {
            const computedStyle = window.getComputedStyle(testElement, '::before');
            const fontFamily = computedStyle.getPropertyValue('font-family');
            const content = computedStyle.getPropertyValue('content');
            
            // Font Awesome loaded if font family contains "Font Awesome" or content is not "none"
            this.fontAwesomeLoaded = fontFamily.toLowerCase().includes('font awesome') || 
                                   (content && content !== 'none' && content !== '""');
            
            if (!this.fontAwesomeLoaded && this.checkAttempts >= this.maxAttempts) {
                console.warn('Font Awesome failed to load after', this.maxAttempts, 'attempts');
                this.applyFallbacks();
            } else if (this.fontAwesomeLoaded) {
                console.log('Font Awesome loaded successfully');
                document.body.classList.remove('fa-fallback');
            }
            
            document.body.removeChild(testElement);
        }, 100);
    }

    applyFallbacks() {
        console.log('Applying icon fallbacks...');
        
        // Add fallback class to body
        document.body.classList.add('fa-fallback');
        
        // Try to load backup Font Awesome
        this.loadBackupFontAwesome();
        
        // Apply emoji fallbacks as last resort
        setTimeout(() => {
            if (!this.fontAwesomeLoaded) {
                this.applyEmojiFallbacks();
            }
        }, 1000);
    }

    loadBackupFontAwesome() {
        const backupUrls = [
            'https://use.fontawesome.com/releases/v6.6.0/css/all.css',
            'https://maxcdn.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.min.css',
            'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css'
        ];

        backupUrls.forEach((url, index) => {
            setTimeout(() => {
                const link = document.createElement('link');
                link.rel = 'stylesheet';
                link.href = url;
                link.onload = () => {
                    console.log('Backup Font Awesome loaded from:', url);
                    setTimeout(() => this.checkFontAwesome(), 200);
                };
                link.onerror = () => {
                    console.warn('Failed to load backup Font Awesome from:', url);
                };
                document.head.appendChild(link);
            }, index * 500);
        });
    }

    applyEmojiFallbacks() {
        console.log('Applying emoji fallbacks...');
        
        const iconMappings = {
            'fa-tachometer-alt': '📊',
            'fa-camera': '📷',
            'fa-users': '👥',
            'fa-chart-line': '📈',
            'fa-chart-bar': '📊',
            'fa-calendar': '📅',
            'fa-calendar-alt': '📅',
            'fa-chalkboard-teacher': '👨‍🏫',
            'fa-cog': '⚙️',
            'fa-user-cog': '👤',
            'fa-door-open': '🚪',
            'fa-user': '👤',
            'fa-key': '🔑',
            'fa-qrcode': '📱',
            'fa-sign-out-alt': '🚪',
            'fa-search': '🔍',
            'fa-bars': '☰'
        };

        // Find all Font Awesome icons and replace with emojis
        Object.keys(iconMappings).forEach(className => {
            const elements = document.querySelectorAll(`.${className}`);
            elements.forEach(element => {
                element.innerHTML = iconMappings[className];
                element.style.fontFamily = '"Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", sans-serif';
                element.style.fontStyle = 'normal';
                element.style.fontWeight = 'normal';
            });
        });
    }

    // Public method to manually trigger fallback
    forceFallback() {
        this.fontAwesomeLoaded = false;
        this.applyFallbacks();
    }

    // Public method to check status
    getStatus() {
        return {
            fontAwesomeLoaded: this.fontAwesomeLoaded,
            checkAttempts: this.checkAttempts,
            hasFallbackClass: document.body.classList.contains('fa-fallback')
        };
    }
}

// Initialize the icon fallback system
let iconManager;

document.addEventListener('DOMContentLoaded', function() {
    iconManager = new IconFallbackManager();
    
    // Make it globally accessible for debugging
    window.iconManager = iconManager;
});

// Additional utility functions
window.fixIcons = function() {
    if (iconManager) {
        iconManager.forceFallback();
    }
};

window.checkIconStatus = function() {
    if (iconManager) {
        console.log('Icon Status:', iconManager.getStatus());
    }
};