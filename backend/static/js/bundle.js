// MoxNAS React-Style Dashboard
class MoxNAS {
    constructor() {
        this.state = {
            currentSection: 'dashboard',
            systemData: {
                storage: { totalDisks: 2, totalSpace: '1.8TB', usedSpace: '432GB', availableSpace: '1.4TB' },
                shares: { total: 3, active: 2, smb: 2, nfs: 1, ftp: 0 },
                services: { 
                    smb: { status: 'running', uptime: '2d 14h' },
                    nfs: { status: 'running', uptime: '2d 14h' },
                    ftp: { status: 'stopped', uptime: '0' },
                    web: { status: 'running', uptime: '2d 14h' }
                },
                system: { 
                    cpu: '12%', 
                    memory: '34%', 
                    uptime: '2 days, 14 hours',
                    temperature: '42°C'
                }
            }
        };
        this.init();
    }

    init() {
        this.setupStyles();
        this.setupUI();
        this.setupEventListeners();
        this.loadDashboard();
        this.startDataRefresh();
    }

    setupStyles() {
        const style = document.createElement('style');
        style.textContent = `
            @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;600;700&display=swap');
            
            * { margin: 0; padding: 0; box-sizing: border-box; }
            
            :root {
                /* TrueNAS Color Scheme */
                --truenas-primary: #0d47a1;
                --truenas-primary-dark: #002171;
                --truenas-primary-light: #5472d3;
                --truenas-secondary: #1976d2;
                --truenas-accent: #2196f3;
                --truenas-bg-dark: #1e1e1e;
                --truenas-bg-darker: #121212;
                --truenas-bg-light: #f5f5f5;
                --truenas-sidebar: #263238;
                --truenas-sidebar-dark: #1c252b;
                --truenas-card: #ffffff;
                --truenas-border: #e0e0e0;
                --truenas-text-primary: #212121;
                --truenas-text-secondary: #757575;
                --truenas-text-white: #ffffff;
                --truenas-success: #4caf50;
                --truenas-warning: #ff9800;
                --truenas-error: #f44336;
                --truenas-info: #2196f3;
                --shadow-card: 0 2px 4px rgba(0,0,0,0.1);
                --shadow-elevated: 0 4px 8px rgba(0,0,0,0.15);
            }
            
            body { 
                font-family: 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; 
                background: var(--truenas-bg-light);
                min-height: 100vh;
                color: var(--truenas-text-primary);
                font-size: 14px;
                line-height: 1.5;
            }
            
            #moxnas-app { 
                display: flex; 
                min-height: 100vh; 
                background: var(--truenas-bg-light);
            }
            
            .header { 
                position: fixed; 
                top: 0; 
                left: 0; 
                right: 0; 
                background: var(--truenas-primary);
                color: var(--truenas-text-white); 
                padding: 0 24px; 
                height: 64px;
                z-index: 100; 
                box-shadow: var(--shadow-elevated);
                border-bottom: 1px solid var(--truenas-primary-dark);
                display: flex;
                align-items: center;
            }
            
            .header-content { 
                display: flex; 
                justify-content: space-between; 
                align-items: center; 
                width: 100%;
                max-width: none;
            }
            
            .logo { 
                font-size: 20px; 
                font-weight: 500; 
                color: var(--truenas-text-white);
                display: flex;
                align-items: center;
                gap: 12px;
            }
            
            .logo::before {
                content: '🏠';
                font-size: 24px;
                margin-right: 8px;
            }
            
            .subtitle { 
                color: rgba(255,255,255,0.8); 
                font-size: 13px; 
                font-weight: 400;
                margin-left: 16px;
            }
            
            .status-indicator { 
                display: flex; 
                align-items: center; 
                gap: 8px; 
                background: rgba(255,255,255,0.15);
                backdrop-filter: blur(10px);
                padding: 8px 16px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 400;
                border: 1px solid rgba(255,255,255,0.2);
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }
            
            .status-dot { 
                width: 8px; 
                height: 8px; 
                border-radius: 50%; 
                background: var(--truenas-success); 
                position: relative;
                animation: pulse 2s infinite;
            }
            
            .status-dot::before {
                content: '';
                position: absolute;
                top: -2px;
                left: -2px;
                right: -2px;
                bottom: -2px;
                border-radius: 50%;
                background: var(--truenas-success);
                opacity: 0.3;
                animation: pulse-ring 2s infinite;
            }
            
            @keyframes pulse { 
                0%, 100% { opacity: 1; transform: scale(1); } 
                50% { opacity: 0.8; transform: scale(1.1); } 
            }
            
            @keyframes pulse-ring {
                0% { transform: scale(1); opacity: 0.3; }
                50% { transform: scale(1.5); opacity: 0.1; }
                100% { transform: scale(2); opacity: 0; }
            }
            
            .sidebar { 
                width: 260px; 
                background: var(--truenas-sidebar);
                padding: 0; 
                margin-top: 64px; 
                position: fixed; 
                height: calc(100vh - 64px); 
                overflow-y: auto; 
                border-right: 1px solid var(--truenas-sidebar-dark);
                z-index: 90;
            }
            
            .nav-section {
                padding: 8px 0;
            }
            
            .nav-item { 
                display: flex; 
                align-items: center; 
                gap: 12px; 
                padding: 12px 24px; 
                cursor: pointer; 
                transition: all 0.2s ease;
                position: relative;
                font-weight: 400;
                color: rgba(255,255,255,0.7);
                font-size: 14px;
                border: none;
                background: none;
            }
            
            .nav-item::before {
                content: '';
                position: absolute;
                left: 0;
                top: 0;
                height: 100%;
                width: 3px;
                background: var(--truenas-accent);
                opacity: 0;
                transition: opacity 0.2s ease;
            }
            
            .nav-item:hover { 
                background: rgba(255,255,255,0.08);
                color: var(--truenas-text-white);
            }
            
            .nav-item:hover::before {
                opacity: 1;
            }
            
            .nav-item.active { 
                background: rgba(33, 150, 243, 0.15);
                color: var(--truenas-text-white);
                font-weight: 500;
            }
            
            .nav-item.active::before {
                opacity: 1;
            }
            
            .nav-icon { 
                font-size: 18px; 
                width: 18px;
                text-align: center;
                opacity: 0.8;
                margin-right: 8px;
            }
            
            .nav-item.active .nav-icon {
                opacity: 1;
            }
            
            .nav-footer { 
                border-top: 1px solid rgba(255,255,255,0.1); 
                margin-top: auto; 
                padding-top: 8px; 
            }
            
            .main-content { 
                flex: 1; 
                margin-left: 260px; 
                margin-top: 64px; 
                padding: 24px; 
                background: var(--truenas-bg-light);
                min-height: calc(100vh - 64px);
            }
            
            .dashboard { 
                max-width: none; 
            }
            
            .dashboard-header { 
                margin-bottom: 24px; 
                padding-bottom: 16px;
                border-bottom: 1px solid var(--truenas-border);
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
            }
            
            .dashboard-header h2 { 
                color: var(--truenas-text-primary); 
                margin-bottom: 8px; 
                font-size: 24px;
                font-weight: 500;
            }
            
            .dashboard-header p { 
                color: var(--truenas-text-secondary); 
                font-size: 14px;
                font-weight: 400;
                margin: 0;
                line-height: 1.4;
            }
            
            .refresh-indicator { 
                margin-top: 8px; 
                display: flex; 
                align-items: center; 
                gap: 8px; 
                color: var(--truenas-text-secondary); 
                font-size: 12px; 
                display: inline-flex;
            }
            
            .refresh-dot { 
                width: 6px; 
                height: 6px; 
                border-radius: 50%; 
                background: var(--truenas-success); 
                animation: pulse 2s infinite; 
            }
            
            .dashboard-grid { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); 
                gap: 24px; 
            }
            
            .dashboard-card { 
                background: var(--truenas-card);
                border-radius: 8px; 
                padding: 24px; 
                box-shadow: var(--shadow-card);
                border: 1px solid var(--truenas-border);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                position: relative;
                overflow: hidden;
            }
            
            .dashboard-card::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 3px;
                background: linear-gradient(90deg, var(--truenas-primary), var(--truenas-accent));
                opacity: 0;
                transition: opacity 0.3s ease;
            }
            
            .dashboard-card:hover {
                box-shadow: 0 8px 32px rgba(13, 71, 161, 0.15);
                transform: translateY(-2px);
            }
            
            .dashboard-card:hover::before {
                opacity: 1;
            }
            
            .card-header { 
                display: flex; 
                justify-content: space-between; 
                align-items: center; 
                margin-bottom: 20px; 
                padding-bottom: 12px;
                border-bottom: 1px solid var(--truenas-border);
            }
            
            .card-header h3 { 
                color: var(--truenas-text-primary); 
                font-size: 16px; 
                font-weight: 500;
                display: flex;
                align-items: center;
                gap: 8px;
                margin: 0;
            }
            
            .card-badge { 
                background: var(--truenas-primary); 
                color: var(--truenas-text-white); 
                padding: 4px 12px; 
                border-radius: 4px; 
                font-size: 12px; 
                font-weight: 500;
                line-height: 1.4;
            }
            
            .storage-stats { 
                margin-top: 16px;
            }
            
            .storage-bar { 
                height: 12px; 
                background: linear-gradient(90deg, #f0f0f0, #f8f8f8); 
                border-radius: 6px; 
                margin-bottom: 16px; 
                overflow: hidden; 
                box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
                position: relative;
            }
            
            .storage-used { 
                height: 100%; 
                background: linear-gradient(90deg, var(--truenas-primary), var(--truenas-accent));
                border-radius: 6px;
                transition: width 1.5s cubic-bezier(0.4, 0, 0.2, 1);
                position: relative;
                overflow: hidden;
            }
            
            .storage-used::after {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
                animation: shimmer 2s infinite;
            }
            
            @keyframes shimmer {
                0% { left: -100%; }
                100% { left: 100%; }
            }
            
            .storage-details { 
                display: flex; 
                flex-direction: column; 
                gap: 12px; 
            }
            
            .storage-item { 
                display: flex; 
                justify-content: space-between; 
                align-items: center;
                padding: 8px 0;
                border-bottom: 1px solid #f0f0f0;
            }
            
            .storage-item:last-child {
                border-bottom: none;
            }
            
            .storage-label { 
                color: var(--truenas-text-secondary); 
                font-weight: 400;
                font-size: 13px;
            }
            
            .storage-value { 
                font-weight: 500; 
                color: var(--truenas-text-primary);
                font-size: 13px;
            }
            
            .storage-value.used { 
                color: var(--truenas-warning); 
            }
            
            .storage-value.available { 
                color: var(--truenas-success); 
            }
            
            .shares-grid { 
                display: flex; 
                flex-direction: column; 
                gap: 1rem; 
            }
            
            .share-type { 
                display: flex; 
                align-items: center; 
                gap: 1rem; 
                padding: 1rem;
                background: rgba(0,0,0,0.02);
                border-radius: 12px;
                transition: all 0.3s ease;
                border: 1px solid rgba(0,0,0,0.05);
            }
            
            .share-type:hover {
                background: rgba(102, 126, 234, 0.05);
                transform: translateX(4px);
                border-color: rgba(102, 126, 234, 0.2);
            }
            
            .share-icon { 
                font-size: 1.5rem; 
                width: 50px;
                height: 50px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: var(--primary-gradient);
                border-radius: 12px;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            }
            
            .share-info { 
                display: flex; 
                flex-direction: column; 
                flex: 1;
            }
            
            .share-name { 
                font-weight: 600; 
                color: #1f2937; 
                font-size: 1rem;
                margin-bottom: 0.25rem;
            }
            
            .share-count { 
                font-size: 0.9rem; 
                color: #6b7280; 
                font-weight: 500;
            }
            
            .services-list { 
                display: flex; 
                flex-direction: column; 
                gap: 1rem; 
            }
            
            .service-item { 
                display: flex; 
                justify-content: space-between; 
                align-items: center; 
                padding: 1rem;
                background: rgba(0,0,0,0.02);
                border-radius: 12px;
                transition: all 0.3s ease;
                border: 1px solid rgba(0,0,0,0.05);
            }
            
            .service-item:hover {
                background: rgba(102, 126, 234, 0.05);
                transform: translateX(4px);
                border-color: rgba(102, 126, 234, 0.2);
            }
            
            .service-info { 
                display: flex; 
                flex-direction: column; 
                flex: 1;
            }
            
            .service-name { 
                font-weight: 600; 
                color: #1f2937; 
                text-transform: uppercase; 
                font-size: 0.9rem; 
                letter-spacing: 0.5px;
                margin-bottom: 0.25rem;
            }
            
            .service-uptime { 
                font-size: 0.85rem; 
                color: #6b7280; 
                font-weight: 500;
            }
            
            .service-status { 
                padding: 0.5rem 1rem; 
                border-radius: 20px; 
                font-size: 0.8rem; 
                font-weight: 600; 
                text-transform: uppercase;
                letter-spacing: 0.5px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            
            .service-status.running { 
                background: var(--success-gradient); 
                color: white; 
                box-shadow: 0 4px 15px rgba(76, 175, 80, 0.4);
            }
            
            .service-status.stopped { 
                background: var(--warning-gradient); 
                color: white; 
                box-shadow: 0 4px 15px rgba(244, 67, 54, 0.4);
            }
            
            .system-metrics { 
                display: flex; 
                flex-direction: column; 
                gap: 1.5rem; 
            }
            
            .metric-item { 
                background: rgba(0,0,0,0.02);
                padding: 1rem;
                border-radius: 12px;
                border: 1px solid rgba(0,0,0,0.05);
            }
            
            .metric-header { 
                display: flex; 
                justify-content: space-between; 
                margin-bottom: 0.75rem; 
            }
            
            .metric-label { 
                color: #6b7280; 
                font-weight: 500;
            }
            
            .metric-value { 
                font-weight: 600; 
                color: #1f2937; 
                background: var(--primary-gradient);
                color: white;
                padding: 0.25rem 0.75rem;
                border-radius: 8px;
                font-size: 0.9rem;
            }
            
            .metric-bar { 
                height: 12px; 
                background: linear-gradient(90deg, rgba(0,0,0,0.05), rgba(0,0,0,0.08)); 
                border-radius: 6px; 
                overflow: hidden; 
                position: relative;
                box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
            }
            
            .metric-fill { 
                height: 100%; 
                background: linear-gradient(90deg, var(--truenas-primary), var(--truenas-accent));
                border-radius: 6px;
                position: relative;
                transition: width 1.5s cubic-bezier(0.4, 0, 0.2, 1);
                box-shadow: 0 2px 8px rgba(13, 71, 161, 0.3);
            }
            
            .metric-fill::after {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 100%;
                background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.3) 50%, transparent 100%);
                animation: shimmer 2s infinite;
            }
            
            .system-info { 
                display: flex; 
                flex-direction: column; 
                gap: 0.75rem; 
                margin-top: 1rem; 
            }
            
            .info-item { 
                display: flex; 
                justify-content: space-between; 
                padding: 0.75rem;
                background: rgba(0,0,0,0.02);
                border-radius: 12px;
                transition: all 0.3s ease;
            }
            
            .info-item:hover {
                background: rgba(102, 126, 234, 0.05);
                transform: translateX(4px);
            }
            
            .info-label { 
                color: #6b7280; 
                font-weight: 500;
            }
            
            .info-value { 
                font-weight: 600; 
                color: #1f2937; 
            }
            
            .actions-grid { 
                display: grid; 
                grid-template-columns: repeat(2, 1fr); 
                gap: 1rem; 
            }
            
            .action-btn { 
                display: flex; 
                flex-direction: column; 
                align-items: center; 
                gap: 12px; 
                padding: 20px 16px; 
                border: 1px solid var(--truenas-border); 
                border-radius: 8px; 
                background: var(--truenas-card);
                cursor: pointer; 
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                font-family: inherit;
                position: relative;
                overflow: hidden;
            }
            
            .action-btn::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(13, 71, 161, 0.1), transparent);
                transition: left 0.5s ease;
            }
            
            .action-btn:hover { 
                border-color: var(--truenas-primary);
                box-shadow: 0 8px 24px rgba(13, 71, 161, 0.2);
                transform: translateY(-2px);
            }
            
            .action-btn:hover::before {
                left: 100%;
            }
            
            .action-btn:active {
                transform: translateY(0);
                transition: transform 0.1s ease;
            }
            
            .action-icon { 
                font-size: 28px; 
                color: var(--truenas-primary);
                margin-bottom: 8px;
            }
            
            .action-text { 
                font-size: 13px; 
                color: var(--truenas-text-primary); 
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                text-align: center;
            }
            
            .activity-list { 
                display: flex; 
                flex-direction: column; 
                gap: 1rem; 
            }
            
            .activity-item { 
                display: flex; 
                flex-direction: column; 
                gap: 0.5rem; 
                padding: 1rem;
                background: rgba(0,0,0,0.02);
                border-radius: 12px;
                border: 1px solid rgba(0,0,0,0.05);
                transition: all 0.3s ease;
                position: relative;
            }
            
            .activity-item::before {
                content: '';
                position: absolute;
                left: 0;
                top: 0;
                bottom: 0;
                width: 4px;
                background: var(--primary-gradient);
                border-radius: 0 4px 4px 0;
                opacity: 0;
                transition: opacity 0.3s ease;
            }
            
            .activity-item:hover {
                background: rgba(102, 126, 234, 0.05);
                transform: translateX(8px);
                border-color: rgba(102, 126, 234, 0.2);
            }
            
            .activity-item:hover::before {
                opacity: 1;
            }
            
            .activity-time { 
                font-size: 0.8rem; 
                color: #9ca3af; 
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .activity-text { 
                color: #374151; 
                font-size: 0.95rem; 
                font-weight: 500;
                line-height: 1.4;
            }
            
            /* Responsive Design */
            @media (max-width: 1024px) {
                .main-content { 
                    margin-left: 0; 
                    padding: 16px; 
                }
                .sidebar { 
                    transform: translateX(-260px); 
                    transition: transform 0.3s ease;
                }
                .dashboard-grid { 
                    grid-template-columns: 1fr; 
                }
                .actions-grid { 
                    grid-template-columns: repeat(2, 1fr); 
                }
                .service-cards {
                    grid-template-columns: 1fr;
                }
                .storage-grid {
                    grid-template-columns: 1fr;
                }
                .system-cards {
                    grid-template-columns: 1fr;
                }
            }
            
            @media (max-width: 768px) {
                .header { 
                    padding: 0 16px; 
                    height: 56px;
                }
                .header-content { 
                    flex-direction: row; 
                }
                .main-content {
                    margin-top: 56px;
                    padding: 16px;
                }
                .sidebar {
                    margin-top: 56px;
                    height: calc(100vh - 56px);
                }
                .dashboard-header h2 { 
                    font-size: 20px; 
                }
                .dashboard-card { 
                    padding: 16px; 
                }
                .nav-item { 
                    padding: 10px 16px; 
                }
                .actions-grid { 
                    grid-template-columns: 1fr; 
                }
                .table-header, .table-row {
                    grid-template-columns: 1fr 60px 120px 60px 80px;
                    font-size: 12px;
                    padding: 8px 12px;
                }
            }
            
            /* Enhanced scrollbar */
            ::-webkit-scrollbar { 
                width: 8px; 
            }
            
            ::-webkit-scrollbar-track { 
                background: var(--truenas-bg-light); 
                border-radius: 4px;
            }
            
            ::-webkit-scrollbar-thumb { 
                background: linear-gradient(180deg, var(--truenas-text-secondary), var(--truenas-primary)); 
                border-radius: 4px; 
                transition: all 0.3s ease;
            }
            
            ::-webkit-scrollbar-thumb:hover { 
                background: linear-gradient(180deg, var(--truenas-primary), var(--truenas-primary-dark)); 
            }
            
            /* Loading skeleton */
            .skeleton {
                background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
                background-size: 200% 100%;
                animation: loading 1.5s infinite;
                border-radius: 4px;
            }
            
            @keyframes loading {
                0% { background-position: 200% 0; }
                100% { background-position: -200% 0; }
            }
            
            .skeleton-text {
                height: 16px;
                margin-bottom: 8px;
            }
            
            .skeleton-title {
                height: 24px;
                width: 60%;
                margin-bottom: 16px;
            }
            
            .skeleton-card {
                height: 200px;
                border-radius: 8px;
            }
            
            /* Enhanced gradients */
            .gradient-bg {
                background: linear-gradient(135deg, var(--truenas-primary), var(--truenas-accent));
            }
            
            .gradient-text {
                background: linear-gradient(135deg, var(--truenas-primary), var(--truenas-accent));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            
            .section { 
                max-width: none; 
            }
            
            .section-header { 
                margin-bottom: 24px; 
                padding-bottom: 16px;
                border-bottom: 1px solid var(--truenas-border);
                display: flex; 
                justify-content: space-between; 
                align-items: flex-start; 
            }
            
            .section-header h2 { 
                color: var(--truenas-text-primary); 
                margin-bottom: 8px; 
                font-size: 24px;
                font-weight: 500;
            }
            
            .section-header p { 
                color: var(--truenas-text-secondary); 
                font-size: 14px;
                margin: 0;
                line-height: 1.4;
            }
            .btn { 
                padding: 10px 20px; 
                border: 1px solid var(--truenas-border); 
                border-radius: 6px; 
                cursor: pointer; 
                font-weight: 500; 
                font-size: 14px;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); 
                text-transform: uppercase;
                letter-spacing: 0.5px;
                font-family: inherit;
                position: relative;
                overflow: hidden;
                white-space: nowrap;
                outline: none;
            }
            
            .btn::before {
                content: '';
                position: absolute;
                top: 50%;
                left: 50%;
                width: 0;
                height: 0;
                background: rgba(255, 255, 255, 0.3);
                border-radius: 50%;
                transform: translate(-50%, -50%);
                transition: width 0.3s ease, height 0.3s ease;
            }
            
            .btn:active::before {
                width: 300px;
                height: 300px;
                transition: width 0.1s ease, height 0.1s ease;
            }
            .btn-primary { 
                background: var(--truenas-primary); 
                color: var(--truenas-text-white); 
                border-color: var(--truenas-primary);
            }
            .btn-primary:hover { 
                background: var(--truenas-primary-dark); 
                border-color: var(--truenas-primary-dark);
                box-shadow: 0 4px 16px rgba(13, 71, 161, 0.3);
                transform: translateY(-1px);
            }
            .btn-secondary { 
                background: transparent; 
                color: var(--truenas-text-primary); 
                border-color: var(--truenas-border);
            }
            .btn-secondary:hover { 
                background: var(--truenas-bg-light); 
                border-color: var(--truenas-primary);
            }
            .btn-danger { 
                background: var(--truenas-error); 
                color: var(--truenas-text-white); 
                border-color: var(--truenas-error);
            }
            .btn-danger:hover { 
                background: #d32f2f; 
                border-color: #d32f2f;
            }
            .btn-small { 
                padding: 6px 12px; 
                font-size: 12px; 
            }
            
            .storage-content { }
            
            .storage-grid { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); 
                gap: 24px; 
            }
            
            .storage-card { 
                background: var(--truenas-card); 
                border-radius: 4px; 
                padding: 24px; 
                box-shadow: var(--shadow-card); 
                border: 1px solid var(--truenas-border);
                transition: all 0.2s ease;
            }
            
            .storage-card:hover {
                box-shadow: var(--shadow-elevated);
            }
            
            .storage-device h3 { 
                color: var(--truenas-text-primary); 
                margin-bottom: 16px; 
                font-size: 16px;
                font-weight: 500;
            }
            
            .device-info { 
                display: flex; 
                justify-content: space-between; 
                margin-bottom: 16px; 
            }
            
            .device-size { 
                color: var(--truenas-text-secondary); 
                font-size: 14px;
            }
            
            .device-status.healthy { 
                color: var(--truenas-success); 
                font-weight: 500; 
                text-transform: uppercase;
                font-size: 12px;
                letter-spacing: 0.5px;
            }
            
            .device-usage { }
            
            .usage-bar { 
                height: 8px; 
                background: #f0f0f0; 
                border-radius: 4px; 
                margin-bottom: 8px; 
                overflow: hidden; 
                border: 1px solid var(--truenas-border);
            }
            
            .usage-fill { 
                height: 100%; 
                background: var(--truenas-primary); 
                transition: width 1s ease;
            }
            
            .usage-text { 
                font-size: 13px; 
                color: var(--truenas-text-secondary); 
            }
            
            .shares-content { }
            .shares-table, .users-table { 
                background: var(--truenas-card); 
                border-radius: 4px; 
                overflow: hidden; 
                box-shadow: var(--shadow-card); 
                border: 1px solid var(--truenas-border);
            }
            
            .table-header { 
                display: grid; 
                grid-template-columns: 1fr 80px 200px 80px 120px; 
                padding: 12px 16px; 
                background: var(--truenas-bg-light); 
                font-weight: 500; 
                color: var(--truenas-text-primary); 
                border-bottom: 1px solid var(--truenas-border);
                font-size: 14px;
            }
            
            .table-row { 
                display: grid; 
                grid-template-columns: 1fr 80px 200px 80px 120px; 
                padding: 12px 16px; 
                border-bottom: 1px solid var(--truenas-border); 
                align-items: center;
                font-size: 14px;
                transition: background 0.2s ease;
            }
            
            .table-row:last-child { 
                border-bottom: none; 
            }
            
            .table-row:hover {
                background: rgba(13, 71, 161, 0.04);
            }
            .share-type { 
                padding: 4px 8px; 
                border-radius: 4px; 
                font-size: 12px; 
                font-weight: 500; 
                text-align: center; 
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .share-type.smb { 
                background: rgba(13, 71, 161, 0.1); 
                color: var(--truenas-primary); 
            }
            
            .share-type.nfs { 
                background: rgba(76, 175, 80, 0.1); 
                color: var(--truenas-success); 
            }
            
            .share-status.active { 
                color: var(--truenas-success); 
                font-weight: 500; 
                text-transform: uppercase;
                font-size: 12px;
                letter-spacing: 0.5px;
            }
            
            .share-status.inactive { 
                color: var(--truenas-text-secondary); 
                font-weight: 500; 
                text-transform: uppercase;
                font-size: 12px;
                letter-spacing: 0.5px;
            }
            .share-actions { display: flex; gap: 0.5rem; }
            
            .services-content { }
            
            .service-cards { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); 
                gap: 24px; 
            }
            
            .service-card { 
                background: var(--truenas-card); 
                border-radius: 4px; 
                padding: 24px; 
                box-shadow: var(--shadow-card); 
                border: 1px solid var(--truenas-border);
                transition: all 0.2s ease;
            }
            
            .service-card:hover {
                box-shadow: var(--shadow-elevated);
            }
            
            .service-header { 
                display: flex; 
                justify-content: space-between; 
                align-items: center; 
                margin-bottom: 16px; 
                padding-bottom: 12px;
                border-bottom: 1px solid var(--truenas-border);
            }
            
            .service-header h3 { 
                color: var(--truenas-text-primary); 
                flex: 1; 
                font-size: 16px;
                font-weight: 500;
                margin: 0;
            }
            
            .service-details p { 
                color: var(--truenas-text-secondary); 
                margin-bottom: 16px; 
                font-size: 14px;
                line-height: 1.4;
            }
            
            .service-stats { 
                display: flex; 
                gap: 16px; 
                margin-bottom: 16px; 
            }
            
            .service-stats span { 
                font-size: 13px; 
                color: var(--truenas-text-secondary); 
            }
            
            .service-actions { 
                display: flex; 
                gap: 12px; 
            }
            
            .users-content { }
            
            .user-actions, .share-actions { 
                display: flex; 
                gap: 8px; 
            }
            
            .network-content { }
            
            .network-card { 
                background: var(--truenas-card); 
                border-radius: 4px; 
                padding: 24px; 
                box-shadow: var(--shadow-card); 
                border: 1px solid var(--truenas-border);
            }
            
            .network-card h3 { 
                color: var(--truenas-text-primary); 
                margin-bottom: 16px; 
                font-size: 16px;
                font-weight: 500;
            }
            
            .interface-item { 
                display: flex; 
                justify-content: space-between; 
                align-items: center; 
                padding: 12px 0; 
                border-bottom: 1px solid var(--truenas-border); 
            }
            
            .interface-item:last-child { 
                border-bottom: none; 
            }
            
            .interface-info { 
                display: flex; 
                flex-direction: column; 
            }
            
            .interface-name { 
                font-weight: 500; 
                color: var(--truenas-text-primary); 
                font-size: 14px;
            }
            
            .interface-ip { 
                font-size: 13px; 
                color: var(--truenas-text-secondary); 
                font-family: 'Courier New', monospace; 
            }
            
            .interface-status.up { 
                color: var(--truenas-success); 
                font-weight: 500; 
                text-transform: uppercase;
                font-size: 12px;
                letter-spacing: 0.5px;
            }
            
            .system-content { }
            
            .system-cards { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); 
                gap: 24px; 
            }
            
            .system-card { 
                background: var(--truenas-card); 
                border-radius: 4px; 
                padding: 24px; 
                box-shadow: var(--shadow-card); 
                border: 1px solid var(--truenas-border);
            }
            
            .system-card h3 { 
                color: var(--truenas-text-primary); 
                margin-bottom: 16px; 
                font-size: 16px;
                font-weight: 500;
            }
            
            .system-details { 
                display: flex; 
                flex-direction: column; 
                gap: 12px; 
            }
            
            .detail-item { 
                display: flex; 
                justify-content: space-between; 
                padding: 8px 0;
                border-bottom: 1px solid #f0f0f0;
            }
            
            .detail-item:last-child { 
                border-bottom: none; 
            }
            
            .detail-label { 
                color: var(--truenas-text-secondary); 
                font-size: 13px;
            }
            
            .detail-value { 
                font-weight: 500; 
                color: var(--truenas-text-primary); 
                font-size: 13px;
            }
        `;
        document.head.appendChild(style);
    }

    setupUI() {
        document.body.innerHTML = `
            <div id="moxnas-app">
                <header class="header">
                    <div class="header-content">
                        <div>
                            <h1 class="logo">🏠 MoxNAS</h1>
                            <p class="subtitle">Network Attached Storage Dashboard</p>
                        </div>
                        <div class="status-indicator">
                            <span class="status-dot"></span>
                            <span>System Online</span>
                        </div>
                    </div>
                </header>
                
                <nav class="sidebar">
                    <div class="nav-section">
                        <div class="nav-item active" data-section="dashboard">
                            <span class="nav-icon">📊</span>
                            Dashboard
                        </div>
                        <div class="nav-item" data-section="storage">
                            <span class="nav-icon">💾</span>
                            Storage
                        </div>
                        <div class="nav-item" data-section="shares">
                            <span class="nav-icon">📁</span>
                            Shares
                        </div>
                        <div class="nav-item" data-section="services">
                            <span class="nav-icon">⚙️</span>
                            Services
                        </div>
                        <div class="nav-item" data-section="users">
                            <span class="nav-icon">👥</span>
                            Users
                        </div>
                        <div class="nav-item" data-section="network">
                            <span class="nav-icon">🌐</span>
                            Network
                        </div>
                        <div class="nav-item" data-section="system">
                            <span class="nav-icon">🖥️</span>
                            System
                        </div>
                    </div>
                    
                    <div class="nav-footer">
                        <div class="nav-item" onclick="window.open('/admin/', '_blank')">
                            <span class="nav-icon">🔧</span>
                            Admin Panel
                        </div>
                    </div>
                </nav>
                
                <main class="main-content">
                    <div id="content-area"></div>
                </main>
            </div>
        `;
    }

    setupEventListeners() {
        document.querySelectorAll('.nav-item[data-section]').forEach(item => {
            item.addEventListener('click', (e) => {
                const section = e.currentTarget.dataset.section;
                this.loadSection(section);
                
                document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
                e.currentTarget.classList.add('active');
            });
        });
    }

    loadSection(section) {
        this.state.currentSection = section;
        
        switch(section) {
            case 'dashboard':
                this.loadDashboard();
                break;
            case 'storage':
                this.loadStorageSection();
                break;
            case 'shares':
                this.loadSharesSection();
                break;
            case 'services':
                this.loadServicesSection();
                break;
            case 'users':
                this.loadUsersSection();
                break;
            case 'network':
                this.loadNetworkSection();
                break;
            case 'system':
                this.loadSystemSection();
                break;
        }
    }

    loadDashboard() {
        const contentArea = document.getElementById('content-area');
        const { storage, shares, services, system } = this.state.systemData;
        
        contentArea.innerHTML = `
            <div class="dashboard">
                <div class="dashboard-header">
                    <div>
                        <h2>System Dashboard</h2>
                        <p>Overview of your MoxNAS system status and resources</p>
                        <div class="refresh-indicator">
                            <span class="refresh-dot"></span>
                            Last updated: ${new Date().toLocaleTimeString()}
                        </div>
                    </div>
                    <button class="btn btn-secondary" onclick="moxnas.refreshData()" style="height: fit-content;">
                        🔄 Refresh
                    </button>
                </div>
                
                <div class="dashboard-grid">
                    <div class="dashboard-card storage-overview">
                        <div class="card-header">
                            <h3>💾 Storage Overview</h3>
                            <span class="card-badge">${storage.totalDisks} Disks</span>
                        </div>
                        <div class="storage-stats">
                            <div class="storage-bar">
                                <div class="storage-used" style="width: 24%"></div>
                            </div>
                            <div class="storage-details">
                                <div class="storage-item">
                                    <span class="storage-label">Total Space</span>
                                    <span class="storage-value">${storage.totalSpace}</span>
                                </div>
                                <div class="storage-item">
                                    <span class="storage-label">Used</span>
                                    <span class="storage-value used">${storage.usedSpace}</span>
                                </div>
                                <div class="storage-item">
                                    <span class="storage-label">Available</span>
                                    <span class="storage-value available">${storage.availableSpace}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="dashboard-card shares-overview">
                        <div class="card-header">
                            <h3>📁 Active Shares</h3>
                            <span class="card-badge">${shares.active}/${shares.total}</span>
                        </div>
                        <div class="shares-grid">
                            <div class="share-type">
                                <span class="share-icon">🖥️</span>
                                <div class="share-info">
                                    <span class="share-name">SMB/CIFS</span>
                                    <span class="share-count">${shares.smb} shares</span>
                                </div>
                            </div>
                            <div class="share-type">
                                <span class="share-icon">🌐</span>
                                <div class="share-info">
                                    <span class="share-name">NFS</span>
                                    <span class="share-count">${shares.nfs} shares</span>
                                </div>
                            </div>
                            <div class="share-type">
                                <span class="share-icon">📤</span>
                                <div class="share-info">
                                    <span class="share-name">FTP</span>
                                    <span class="share-count">${shares.ftp} shares</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="dashboard-card services-overview">
                        <div class="card-header">
                            <h3>⚙️ System Services</h3>
                            <span class="card-badge">3/4 Running</span>
                        </div>
                        <div class="services-list">
                            ${Object.entries(services).map(([service, data]) => `
                                <div class="service-item">
                                    <div class="service-info">
                                        <span class="service-name">${service.toUpperCase()}</span>
                                        <span class="service-uptime">${data.uptime}</span>
                                    </div>
                                    <span class="service-status ${data.status}">${data.status}</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    
                    <div class="dashboard-card system-overview">
                        <div class="card-header">
                            <h3>🖥️ System Resources</h3>
                            <span class="card-badge">Healthy</span>
                        </div>
                        <div class="system-metrics">
                            <div class="metric-item">
                                <div class="metric-header">
                                    <span class="metric-label">CPU Usage</span>
                                    <span class="metric-value">${system.cpu}</span>
                                </div>
                                <div class="metric-bar">
                                    <div class="metric-fill" style="width: ${system.cpu}"></div>
                                </div>
                            </div>
                            <div class="metric-item">
                                <div class="metric-header">
                                    <span class="metric-label">Memory</span>
                                    <span class="metric-value">${system.memory}</span>
                                </div>
                                <div class="metric-bar">
                                    <div class="metric-fill" style="width: ${system.memory}"></div>
                                </div>
                            </div>
                            <div class="system-info">
                                <div class="info-item">
                                    <span class="info-label">Uptime</span>
                                    <span class="info-value">${system.uptime}</span>
                                </div>
                                <div class="info-item">
                                    <span class="info-label">Temperature</span>
                                    <span class="info-value">${system.temperature}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="dashboard-card quick-actions">
                        <div class="card-header">
                            <h3>⚡ Quick Actions</h3>
                        </div>
                        <div class="actions-grid">
                            <button class="action-btn" onclick="moxnas.loadSection('storage')">
                                <span class="action-icon">💾</span>
                                <span class="action-text">Manage Storage</span>
                            </button>
                            <button class="action-btn" onclick="moxnas.loadSection('shares')">
                                <span class="action-icon">📁</span>
                                <span class="action-text">Create Share</span>
                            </button>
                            <button class="action-btn" onclick="moxnas.loadSection('users')">
                                <span class="action-icon">👥</span>
                                <span class="action-text">Add User</span>
                            </button>
                            <button class="action-btn" onclick="window.open('/admin/', '_blank')">
                                <span class="action-icon">🔧</span>
                                <span class="action-text">Admin Panel</span>
                            </button>
                        </div>
                    </div>
                    
                    <div class="dashboard-card recent-activity">
                        <div class="card-header">
                            <h3>📋 Recent Activity</h3>
                        </div>
                        <div class="activity-list">
                            <div class="activity-item">
                                <span class="activity-time">2 minutes ago</span>
                                <span class="activity-text">SMB share 'Documents' accessed by user admin</span>
                            </div>
                            <div class="activity-item">
                                <span class="activity-time">15 minutes ago</span>
                                <span class="activity-text">Storage pool 'main-pool' health check completed</span>
                            </div>
                            <div class="activity-item">
                                <span class="activity-time">1 hour ago</span>
                                <span class="activity-text">NFS service restarted successfully</span>
                            </div>
                            <div class="activity-item">
                                <span class="activity-time">3 hours ago</span>
                                <span class="activity-text">New user 'guest' created</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    loadStorageSection() {
        const contentArea = document.getElementById('content-area');
        contentArea.innerHTML = `
            <div class="section">
                <div class="section-header">
                    <div>
                        <h2>💾 Storage Management</h2>
                        <p>Manage disks, mount points, and storage pools</p>
                    </div>
                    <button class="btn btn-primary" onclick="moxnas.addStorageDevice()">Add Storage Device</button>
                </div>
                <div class="storage-content">
                    <div class="storage-grid">
                        <div class="storage-card">
                            <div class="storage-device">
                                <h3>/dev/sda</h3>
                                <div class="device-info">
                                    <span class="device-size">1TB SSD</span>
                                    <span class="device-status healthy">Healthy</span>
                                </div>
                                <div class="device-usage">
                                    <div class="usage-bar">
                                        <div class="usage-fill" style="width: 65%"></div>
                                    </div>
                                    <span class="usage-text">650GB / 1TB used</span>
                                </div>
                            </div>
                        </div>
                        <div class="storage-card">
                            <div class="storage-device">
                                <h3>/dev/sdb</h3>
                                <div class="device-info">
                                    <span class="device-size">800GB HDD</span>
                                    <span class="device-status healthy">Healthy</span>
                                </div>
                                <div class="device-usage">
                                    <div class="usage-bar">
                                        <div class="usage-fill" style="width: 30%"></div>
                                    </div>
                                    <span class="usage-text">240GB / 800GB used</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    loadSharesSection() {
        const contentArea = document.getElementById('content-area');
        contentArea.innerHTML = `
            <div class="section">
                <div class="section-header">
                    <div>
                        <h2>📁 Share Management</h2>
                        <p>Configure SMB, NFS, and FTP shares</p>
                    </div>
                    <button class="btn btn-primary" onclick="moxnas.createNewShare()">Create New Share</button>
                </div>
                <div class="shares-content">
                    <div class="shares-table">
                        <div class="table-header">
                            <span>Share Name</span>
                            <span>Type</span>
                            <span>Path</span>
                            <span>Status</span>
                            <span>Actions</span>
                        </div>
                        <div class="table-row">
                            <span class="share-name">Documents</span>
                            <span class="share-type smb">SMB</span>
                            <span class="share-path">/mnt/storage/documents</span>
                            <span class="share-status active">Active</span>
                            <div class="share-actions">
                                <button class="btn btn-small btn-secondary" onclick="moxnas.editItem('share', 'Documents')">Edit</button>
                                <button class="btn btn-small btn-danger" onclick="moxnas.controlService('SMB Documents', 'stop')">Stop</button>
                            </div>
                        </div>
                        <div class="table-row">
                            <span class="share-name">Media</span>
                            <span class="share-type nfs">NFS</span>
                            <span class="share-path">/mnt/storage/media</span>
                            <span class="share-status active">Active</span>
                            <div class="share-actions">
                                <button class="btn btn-small btn-secondary" onclick="moxnas.editItem('share', 'Media')">Edit</button>
                                <button class="btn btn-small btn-danger" onclick="moxnas.controlService('NFS Media', 'stop')">Stop</button>
                            </div>
                        </div>
                        <div class="table-row">
                            <span class="share-name">Backup</span>
                            <span class="share-type smb">SMB</span>
                            <span class="share-path">/mnt/storage/backup</span>
                            <span class="share-status inactive">Inactive</span>
                            <div class="share-actions">
                                <button class="btn btn-small btn-secondary" onclick="moxnas.editItem('share', 'Backup')">Edit</button>
                                <button class="btn btn-small btn-primary" onclick="moxnas.controlService('SMB Backup', 'start')">Start</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    loadServicesSection() {
        const contentArea = document.getElementById('content-area');
        contentArea.innerHTML = `
            <div class="section">
                <div class="section-header">
                    <div>
                        <h2>⚙️ Service Management</h2>
                        <p>Monitor and control system services</p>
                    </div>
                </div>
                <div class="services-content">
                    <div class="service-cards">
                        <div class="service-card">
                            <div class="service-header">
                                <h3>SMB/CIFS Service</h3>
                                <span class="service-status running">Running</span>
                            </div>
                            <div class="service-details">
                                <p>Provides Windows file sharing via SMB protocol</p>
                                <div class="service-stats">
                                    <span>Uptime: 2d 14h</span>
                                    <span>Connections: 3</span>
                                </div>
                            </div>
                            <div class="service-actions">
                                <button class="btn btn-secondary" onclick="moxnas.controlService('SMB/CIFS', 'restart')">Restart</button>
                                <button class="btn btn-danger" onclick="moxnas.controlService('SMB/CIFS', 'stop')">Stop</button>
                            </div>
                        </div>
                        
                        <div class="service-card">
                            <div class="service-header">
                                <h3>NFS Service</h3>
                                <span class="service-status running">Running</span>
                            </div>
                            <div class="service-details">
                                <p>Network File System for Unix/Linux clients</p>
                                <div class="service-stats">
                                    <span>Uptime: 2d 14h</span>
                                    <span>Exports: 1</span>
                                </div>
                            </div>
                            <div class="service-actions">
                                <button class="btn btn-secondary" onclick="moxnas.controlService('NFS', 'restart')">Restart</button>
                                <button class="btn btn-danger" onclick="moxnas.controlService('NFS', 'stop')">Stop</button>
                            </div>
                        </div>
                        
                        <div class="service-card">
                            <div class="service-header">
                                <h3>FTP Service</h3>
                                <span class="service-status stopped">Stopped</span>
                            </div>
                            <div class="service-details">
                                <p>File Transfer Protocol service</p>
                                <div class="service-stats">
                                    <span>Uptime: 0</span>
                                    <span>Connections: 0</span>
                                </div>
                            </div>
                            <div class="service-actions">
                                <button class="btn btn-primary" onclick="moxnas.controlService('FTP', 'start')">Start</button>
                                <button class="btn btn-secondary" onclick="moxnas.editItem('service', 'FTP')">Configure</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    loadUsersSection() {
        const contentArea = document.getElementById('content-area');
        contentArea.innerHTML = `
            <div class="section">
                <div class="section-header">
                    <div>
                        <h2>👥 User Management</h2>
                        <p>Manage user accounts and permissions</p>
                    </div>
                    <button class="btn btn-primary" onclick="moxnas.addNewUser()">Add New User</button>
                </div>
                <div class="users-content">
                    <div class="users-table">
                        <div class="table-header">
                            <span>Username</span>
                            <span>Full Name</span>
                            <span>Groups</span>
                            <span>Last Login</span>
                            <span>Actions</span>
                        </div>
                        <div class="table-row">
                            <span class="username">admin</span>
                            <span class="fullname">Administrator</span>
                            <span class="groups">admin, users</span>
                            <span class="last-login">2 hours ago</span>
                            <div class="user-actions">
                                <button class="btn btn-small btn-secondary" onclick="moxnas.editItem('user', 'admin')">Edit</button>
                                <button class="btn btn-small btn-secondary" onclick="moxnas.resetPassword('admin')">Reset Password</button>
                            </div>
                        </div>
                        <div class="table-row">
                            <span class="username">guest</span>
                            <span class="fullname">Guest User</span>
                            <span class="groups">users</span>
                            <span class="last-login">Never</span>
                            <div class="user-actions">
                                <button class="btn btn-small btn-secondary" onclick="moxnas.editItem('user', 'guest')">Edit</button>
                                <button class="btn btn-small btn-danger" onclick="moxnas.deleteItem('user', 'guest')">Delete</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    loadNetworkSection() {
        const contentArea = document.getElementById('content-area');
        contentArea.innerHTML = `
            <div class="section">
                <div class="section-header">
                    <div>
                        <h2>🌐 Network Settings</h2>
                        <p>Configure network interfaces and settings</p>
                    </div>
                </div>
                <div class="network-content">
                    <div class="network-card">
                        <h3>Network Interfaces</h3>
                        <div class="interface-item">
                            <div class="interface-info">
                                <span class="interface-name">eth0</span>
                                <span class="interface-ip">192.168.1.100/24</span>
                            </div>
                            <span class="interface-status up">Up</span>
                        </div>
                        <div class="interface-item">
                            <div class="interface-info">
                                <span class="interface-name">lo</span>
                                <span class="interface-ip">127.0.0.1/8</span>
                            </div>
                            <span class="interface-status up">Up</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    loadSystemSection() {
        const contentArea = document.getElementById('content-area');
        const { system } = this.state.systemData;
        
        contentArea.innerHTML = `
            <div class="section">
                <div class="section-header">
                    <div>
                        <h2>🖥️ System Information</h2>
                        <p>View system status and information</p>
                    </div>
                </div>
                <div class="system-content">
                    <div class="system-cards">
                        <div class="system-card">
                            <h3>System Overview</h3>
                            <div class="system-details">
                                <div class="detail-item">
                                    <span class="detail-label">Operating System</span>
                                    <span class="detail-value">Linux (MoxNAS)</span>
                                </div>
                                <div class="detail-item">
                                    <span class="detail-label">Uptime</span>
                                    <span class="detail-value">${system.uptime}</span>
                                </div>
                                <div class="detail-item">
                                    <span class="detail-label">CPU Usage</span>
                                    <span class="detail-value">${system.cpu}</span>
                                </div>
                                <div class="detail-item">
                                    <span class="detail-label">Memory Usage</span>
                                    <span class="detail-value">${system.memory}</span>
                                </div>
                                <div class="detail-item">
                                    <span class="detail-label">Temperature</span>
                                    <span class="detail-value">${system.temperature}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    startDataRefresh() {
        setInterval(() => {
            if (this.state.currentSection === 'dashboard') {
                // Update timestamp
                const refreshIndicator = document.querySelector('.refresh-indicator');
                if (refreshIndicator) {
                    refreshIndicator.innerHTML = `
                        <span class="refresh-dot"></span>
                        Last updated: ${new Date().toLocaleTimeString()}
                    `;
                }
                
                // Simulate minor data changes
                this.state.systemData.system.cpu = `${Math.floor(Math.random() * 20 + 5)}%`;
                this.state.systemData.system.memory = `${Math.floor(Math.random() * 15 + 25)}%`;
            }
        }, 30000); // Refresh every 30 seconds
    }

    // Button functionality methods
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-icon">${type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'}</span>
                <span class="notification-message">${message}</span>
            </div>
        `;
        
        // Add notification styles if not present
        if (!document.querySelector('#notification-styles')) {
            const notificationStyles = document.createElement('style');
            notificationStyles.id = 'notification-styles';
            notificationStyles.textContent = `
                .notification {
                    position: fixed;
                    top: 120px;
                    right: 20px;
                    background: rgba(255, 255, 255, 0.95);
                    backdrop-filter: blur(20px);
                    border-radius: 12px;
                    padding: 1rem 1.5rem;
                    box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    z-index: 1000;
                    animation: slideIn 0.3s ease-out;
                }
                .notification-success { border-left: 4px solid #4CAF50; }
                .notification-error { border-left: 4px solid #f44336; }
                .notification-info { border-left: 4px solid #2196F3; }
                .notification-content { display: flex; align-items: center; gap: 0.75rem; }
                .notification-message { font-weight: 500; color: #374151; }
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
            `;
            document.head.appendChild(notificationStyles);
        }
        
        document.body.appendChild(notification);
        setTimeout(() => {
            notification.style.animation = 'slideIn 0.3s ease-out reverse';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    showModal(title, content, buttons = []) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>${title}</h3>
                    <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button>
                </div>
                <div class="modal-body">
                    ${content}
                </div>
                <div class="modal-footer">
                    ${buttons.map(btn => `<button class="btn ${btn.class}" onclick="${btn.onclick}">${btn.text}</button>`).join('')}
                    <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">Cancel</button>
                </div>
            </div>
        `;

        // Add modal styles if not present
        if (!document.querySelector('#modal-styles')) {
            const modalStyles = document.createElement('style');
            modalStyles.id = 'modal-styles';
            modalStyles.textContent = `
                .modal-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.5);
                    backdrop-filter: blur(5px);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 2000;
                    animation: fadeIn 0.3s ease-out;
                }
                .modal-content {
                    background: rgba(255, 255, 255, 0.95);
                    backdrop-filter: blur(20px);
                    border-radius: 16px;
                    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    min-width: 400px;
                    max-width: 600px;
                    max-height: 80vh;
                    overflow: hidden;
                    animation: slideUp 0.3s ease-out;
                }
                .modal-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 1.5rem;
                    border-bottom: 1px solid rgba(0, 0, 0, 0.1);
                }
                .modal-header h3 {
                    color: #1f2937;
                    font-weight: 600;
                }
                .modal-close {
                    background: none;
                    border: none;
                    font-size: 1.5rem;
                    cursor: pointer;
                    color: #6b7280;
                    padding: 0.25rem;
                    border-radius: 4px;
                    transition: background 0.2s;
                }
                .modal-close:hover {
                    background: rgba(0, 0, 0, 0.1);
                }
                .modal-body {
                    padding: 1.5rem;
                    max-height: 400px;
                    overflow-y: auto;
                }
                .modal-footer {
                    display: flex;
                    gap: 1rem;
                    padding: 1.5rem;
                    border-top: 1px solid rgba(0, 0, 0, 0.1);
                    justify-content: flex-end;
                }
                @keyframes fadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
                @keyframes slideUp {
                    from { transform: translateY(30px); opacity: 0; }
                    to { transform: translateY(0); opacity: 1; }
                }
                .form-group {
                    margin-bottom: 1rem;
                }
                .form-label {
                    display: block;
                    margin-bottom: 0.5rem;
                    font-weight: 500;
                    color: #374151;
                }
                .form-input, .form-select {
                    width: 100%;
                    padding: 0.75rem;
                    border: 1px solid #d1d5db;
                    border-radius: 8px;
                    font-size: 0.9rem;
                    transition: border-color 0.2s;
                }
                .form-input:focus, .form-select:focus {
                    outline: none;
                    border-color: #667eea;
                    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
                }
            `;
            document.head.appendChild(modalStyles);
        }

        document.body.appendChild(modal);
    }

    // Storage Management Functions
    addStorageDevice() {
        const content = `
            <div class="form-group">
                <label class="form-label">Device Path</label>
                <input type="text" class="form-input" placeholder="/dev/sdc" id="device-path">
            </div>
            <div class="form-group">
                <label class="form-label">Device Name</label>
                <input type="text" class="form-input" placeholder="Storage Drive 3" id="device-name">
            </div>
            <div class="form-group">
                <label class="form-label">File System</label>
                <select class="form-select" id="device-filesystem">
                    <option value="ext4">ext4</option>
                    <option value="xfs">XFS</option>
                    <option value="btrfs">Btrfs</option>
                    <option value="zfs">ZFS</option>
                </select>
            </div>
        `;
        
        this.showModal('Add Storage Device', content, [{
            text: 'Add Device',
            class: 'btn-primary',
            onclick: 'moxnas.confirmAddStorage()'
        }]);
    }

    confirmAddStorage() {
        const path = document.getElementById('device-path').value;
        const name = document.getElementById('device-name').value;
        const filesystem = document.getElementById('device-filesystem').value;
        
        if (!path || !name) {
            this.showNotification('Please fill in all required fields', 'error');
            return;
        }
        
        document.querySelector('.modal-overlay').remove();
        this.showNotification(`Storage device "${name}" added successfully`, 'success');
    }

    // Share Management Functions
    createNewShare() {
        const content = `
            <div class="form-group">
                <label class="form-label">Share Name</label>
                <input type="text" class="form-input" placeholder="MyShare" id="share-name">
            </div>
            <div class="form-group">
                <label class="form-label">Share Type</label>
                <select class="form-select" id="share-type">
                    <option value="smb">SMB/CIFS</option>
                    <option value="nfs">NFS</option>
                    <option value="ftp">FTP</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">Path</label>
                <input type="text" class="form-input" placeholder="/mnt/storage/myshare" id="share-path">
            </div>
            <div class="form-group">
                <label class="form-label">Description</label>
                <input type="text" class="form-input" placeholder="Share description" id="share-description">
            </div>
        `;
        
        this.showModal('Create New Share', content, [{
            text: 'Create Share',
            class: 'btn-primary',
            onclick: 'moxnas.confirmCreateShare()'
        }]);
    }

    confirmCreateShare() {
        const name = document.getElementById('share-name').value;
        const type = document.getElementById('share-type').value;
        const path = document.getElementById('share-path').value;
        
        if (!name || !path) {
            this.showNotification('Please fill in all required fields', 'error');
            return;
        }
        
        document.querySelector('.modal-overlay').remove();
        this.showNotification(`${type.toUpperCase()} share "${name}" created successfully`, 'success');
    }

    // User Management Functions
    addNewUser() {
        const content = `
            <div class="form-group">
                <label class="form-label">Username</label>
                <input type="text" class="form-input" placeholder="username" id="user-name">
            </div>
            <div class="form-group">
                <label class="form-label">Full Name</label>
                <input type="text" class="form-input" placeholder="Full Name" id="user-fullname">
            </div>
            <div class="form-group">
                <label class="form-label">Password</label>
                <input type="password" class="form-input" placeholder="Password" id="user-password">
            </div>
            <div class="form-group">
                <label class="form-label">Groups</label>
                <select class="form-select" id="user-groups" multiple>
                    <option value="users">users</option>
                    <option value="admin">admin</option>
                    <option value="smb">smb</option>
                </select>
            </div>
        `;
        
        this.showModal('Add New User', content, [{
            text: 'Create User',
            class: 'btn-primary',
            onclick: 'moxnas.confirmAddUser()'
        }]);
    }

    confirmAddUser() {
        const username = document.getElementById('user-name').value;
        const fullname = document.getElementById('user-fullname').value;
        const password = document.getElementById('user-password').value;
        
        if (!username || !password) {
            this.showNotification('Username and password are required', 'error');
            return;
        }
        
        document.querySelector('.modal-overlay').remove();
        this.showNotification(`User "${username}" created successfully`, 'success');
    }

    // Service Management Functions
    controlService(serviceName, action) {
        this.showNotification(`${action.charAt(0).toUpperCase() + action.slice(1)}ing ${serviceName} service...`, 'info');
        
        // Simulate service control
        setTimeout(() => {
            this.showNotification(`${serviceName} service ${action}ed successfully`, 'success');
            
            // Update service status in the UI
            const statusElements = document.querySelectorAll('.service-status');
            statusElements.forEach(element => {
                const serviceItem = element.closest('.service-item');
                if (serviceItem && serviceItem.textContent.toLowerCase().includes(serviceName.toLowerCase())) {
                    if (action === 'start') {
                        element.className = 'service-status running';
                        element.textContent = 'running';
                    } else if (action === 'stop') {
                        element.className = 'service-status stopped';
                        element.textContent = 'stopped';
                    }
                }
            });
        }, 1500);
    }

    // Loading state management
    showLoadingState(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = `
                <div class="skeleton-card skeleton"></div>
            `;
        }
    }

    // Enhanced data refresh with loading states
    refreshData() {
        this.showNotification('Refreshing system data...', 'info');
        
        // Simulate loading
        setTimeout(() => {
            // Update timestamp
            const refreshIndicator = document.querySelector('.refresh-indicator');
            if (refreshIndicator) {
                refreshIndicator.innerHTML = `
                    <span class="refresh-dot"></span>
                    Last updated: ${new Date().toLocaleTimeString()}
                `;
            }
            
            // Simulate data changes
            this.state.systemData.system.cpu = `${Math.floor(Math.random() * 20 + 5)}%`;
            this.state.systemData.system.memory = `${Math.floor(Math.random() * 15 + 25)}%`;
            
            this.showNotification('System data refreshed successfully', 'success');
            
            // Reload current section to show updated data
            this.loadSection(this.state.currentSection);
        }, 1000);
    }

    // Generic button handlers
    editItem(type, name) {
        this.showNotification(`Editing ${type}: ${name}`, 'info');
    }

    deleteItem(type, name) {
        const content = `<p>Are you sure you want to delete ${type} "<strong>${name}</strong>"?</p><p>This action cannot be undone.</p>`;
        
        this.showModal('Confirm Deletion', content, [{
            text: 'Delete',
            class: 'btn-danger',
            onclick: `moxnas.confirmDelete('${type}', '${name}')`
        }]);
    }

    confirmDelete(type, name) {
        document.querySelector('.modal-overlay').remove();
        this.showNotification(`${type} "${name}" deleted successfully`, 'success');
    }

    resetPassword(username) {
        const content = `
            <p>Reset password for user "<strong>${username}</strong>"</p>
            <div class="form-group">
                <label class="form-label">New Password</label>
                <input type="password" class="form-input" placeholder="New password" id="new-password">
            </div>
            <div class="form-group">
                <label class="form-label">Confirm Password</label>
                <input type="password" class="form-input" placeholder="Confirm password" id="confirm-password">
            </div>
        `;
        
        this.showModal('Reset Password', content, [{
            text: 'Reset Password',
            class: 'btn-primary',
            onclick: `moxnas.confirmResetPassword('${username}')`
        }]);
    }

    confirmResetPassword(username) {
        const newPassword = document.getElementById('new-password').value;
        const confirmPassword = document.getElementById('confirm-password').value;
        
        if (!newPassword || newPassword !== confirmPassword) {
            this.showNotification('Passwords do not match', 'error');
            return;
        }
        
        document.querySelector('.modal-overlay').remove();
        this.showNotification(`Password reset for "${username}" successfully`, 'success');
    }
}

// Initialize MoxNAS when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.moxnas = new MoxNAS();
});