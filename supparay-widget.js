// Supparay Widget JavaScript
class SupparayWidget {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            position: 'right', // 'right', 'left', or 'inline'
            theme: 'default', // 'default', 'dark', 'light'
            showProfile: true,
            showSocials: true,
            customLinks: [],
            ...options
        };
        
        this.init();
    }
    
    init() {
        if (!this.container) {
            console.error('Supparay Widget: Container not found');
            return;
        }
        
        this.render();
        this.attachEventListeners();
    }
    
    render() {
        const widgetHTML = `
            <div class="supparay-widget ${this.options.position === 'inline' ? '' : 'side-container'} ${this.options.position === 'left' ? 'left' : ''}">
                ${this.options.showProfile ? this.renderProfile() : ''}
                ${this.options.showSocials ? this.renderSocials() : ''}
                <div class="links-container">
                    ${this.renderLinks()}
                </div>
            </div>
        `;
        
        this.container.innerHTML = widgetHTML;
    }
    
    renderProfile() {
        return `
            <div class="profile-section">
                <div class="profile-avatar">
                    <i class="fas fa-user"></i>
                </div>
                <h2 class="profile-name">@supparay</h2>
                <p class="profile-tagline">ORDER SUPPORT FOLLOW ENJOY</p>
            </div>
        `;
    }
    
    renderSocials() {
        const socials = [
            { icon: 'fab fa-instagram', label: 'Instagram', url: 'https://instagram.com/supparay' },
            { icon: 'fab fa-facebook', label: 'Facebook', url: 'https://facebook.com/supparay' },
            { icon: 'fas fa-envelope', label: 'Email', url: 'mailto:contact@supparay.com' },
            { icon: 'fab fa-youtube', label: 'YouTube', url: 'https://youtube.com/@supparay' },
            { icon: 'fab fa-tiktok', label: 'TikTok', url: 'https://tiktok.com/@supparay' },
            { icon: 'fab fa-x-twitter', label: 'X', url: 'https://x.com/supparay' }
        ];
        
        return `
            <div class="social-grid">
                ${socials.map(social => `
                    <a href="${social.url}" target="_blank" class="social-item">
                        <i class="${social.icon} social-icon"></i>
                        <span class="social-label">${social.label}</span>
                    </a>
                `).join('')}
            </div>
        `;
    }
    
    renderLinks() {
        const defaultLinks = [
            { icon: 'fab fa-tiktok', title: 'TikTok', subtitle: 'supparay', url: 'https://tiktok.com/@supparay' },
            { icon: 'fab fa-twitch', title: 'Twitch', subtitle: 'Live Streaming', url: 'https://twitch.tv/supparay' },
            { icon: 'fas fa-store', title: 'Creator Spring', subtitle: 'Official Merchandise', url: 'https://suppa.creator-spring.com' },
            { icon: 'fab fa-spotify', title: 'Spotify Playlist', subtitle: 'Our Music Collection', url: 'https://open.spotify.com/user/supparay' },
            { icon: 'fas fa-heart', title: 'Direct Support', subtitle: 'Fanbase', url: 'https://fanbase.app/supparay' },
            { icon: 'fas fa-donate', title: 'Support', subtitle: 'Direct Donations', url: 'https://paypal.me/supparay' }
        ];
        
        const links = this.options.customLinks.length > 0 ? this.options.customLinks : defaultLinks;
        
        return links.map(link => `
            <a href="${link.url}" target="_blank" class="link-item" data-link="${link.title}">
                <div class="link-icon">
                    <i class="${link.icon}"></i>
                </div>
                <div class="link-content">
                    <div class="link-title">${link.title}</div>
                    <div class="link-subtitle">${link.subtitle}</div>
                </div>
            </a>
        `).join('');
    }
    
    attachEventListeners() {
        // Add click animations and tracking
        this.container.querySelectorAll('.link-item, .social-item').forEach(link => {
            link.addEventListener('click', (e) => {
                // Add click animation
                link.style.transform = 'scale(0.95)';
                setTimeout(() => {
                    link.style.transform = '';
                }, 150);
                
                // Track clicks (optional analytics)
                this.trackClick(link.href, link.dataset.link || link.textContent.trim());
            });
        });
        
        // Enhanced hover effects
        this.container.querySelectorAll('.link-item').forEach(item => {
            item.addEventListener('mouseenter', function() {
                this.style.background = 'rgba(255, 255, 255, 0.25)';
            });
            
            item.addEventListener('mouseleave', function() {
                this.style.background = 'rgba(255, 255, 255, 0.15)';
            });
        });
    }
    
    trackClick(url, linkName) {
        // Optional: Add your analytics tracking here
        console.log('Supparay Widget - Link clicked:', linkName, url);
        
        // Example: Google Analytics tracking
        if (typeof gtag !== 'undefined') {
            gtag('event', 'click', {
                event_category: 'Supparay Widget',
                event_label: linkName,
                value: url
            });
        }
    }
    
    // Method to update links dynamically
    updateLinks(newLinks) {
        this.options.customLinks = newLinks;
        this.render();
        this.attachEventListeners();
    }
    
    // Method to change position
    setPosition(position) {
        this.options.position = position;
        this.render();
        this.attachEventListeners();
    }
}

// Auto-initialize if data attributes are present
document.addEventListener('DOMContentLoaded', function() {
    const autoWidgets = document.querySelectorAll('[data-supparay-widget]');
    autoWidgets.forEach(container => {
        const options = {
            position: container.dataset.position || 'inline',
            showProfile: container.dataset.showProfile !== 'false',
            showSocials: container.dataset.showSocials !== 'false'
        };
        
        new SupparayWidget(container.id, options);
    });
});
