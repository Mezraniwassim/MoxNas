// MoxNAS Form Handlers - Added form submission and autocomplete functionality

/**
 * Form submission handler with API integration
 * 
 * @param {HTMLFormElement} form - The form element to submit
 * @param {string} endpoint - API endpoint URL
 * @param {string} method - HTTP method (POST, PUT, etc)
 * @param {Object} options - Additional options
 * @returns {Promise<Object|boolean>} Result of submission or false on error
 */
MoxNAS.prototype.submitFormToAPI = async function(form, endpoint, method = 'POST', options = {}) {
    // Default options
    const defaults = {
        showLoading: true,
        loadingMessage: 'Processing...',
        successMessage: 'Form submitted successfully',
        errorMessage: 'Error submitting form',
        redirectUrl: null,
        onSuccess: null,
        onError: null
    };
    
    // Merge options
    const settings = { ...defaults, ...options };
    
    // Validate form if data-validate attribute is present
    if (form.hasAttribute('data-validate') && !this.validateForm(form)) {
        this.showToast('Please correct the errors in the form', 'warning');
        return false;
    }
    
    // Show loading state
    if (settings.showLoading) {
        this.showFormLoading(form, settings.loadingMessage);
    }
    
    // Get form data
    const formData = new FormData(form);
    const jsonData = {};
    
    // Convert FormData to JSON object if not multipart/form-data
    if (!form.enctype || form.enctype !== 'multipart/form-data') {
        formData.forEach((value, key) => {
            // Handle array fields (fields with name attribute like name[])
            if (key.endsWith('[]')) {
                const baseKey = key.slice(0, -2);
                if (!jsonData[baseKey]) {
                    jsonData[baseKey] = [];
                }
                jsonData[baseKey].push(value);
            } else {
                jsonData[key] = value;
            }
        });
    }
    
    try {
        // Make API call
        const response = await fetch(endpoint, {
            method: method.toUpperCase(),
            headers: {
                'Content-Type': form.enctype === 'multipart/form-data' ? undefined : 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: form.enctype === 'multipart/form-data' ? formData : JSON.stringify(jsonData)
        });
        
        // Hide loading state
        if (settings.showLoading) {
            this.hideFormLoading(form);
        }
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || errorData.error || `Error ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json().catch(() => ({}));
        
        // Show success message
        this.showToast(data.message || settings.successMessage, 'success');
        
        // Clear form if needed
        if (form.hasAttribute('data-reset-on-success')) {
            form.reset();
            
            // Clear validation styling
            form.querySelectorAll('.error, .valid').forEach(field => {
                field.classList.remove('error', 'valid');
            });
            
            form.querySelectorAll('.field-error').forEach(error => {
                error.style.display = 'none';
                error.textContent = '';
            });
        }
        
        // Call onSuccess callback if provided
        if (typeof settings.onSuccess === 'function') {
            settings.onSuccess(data);
        }
        
        // Redirect if needed
        if (settings.redirectUrl) {
            window.location.href = settings.redirectUrl;
        }
        
        return data;
    } catch (error) {
        // Hide loading state
        if (settings.showLoading) {
            this.hideFormLoading(form);
        }
        
        console.error('Form submission error:', error);
        
        // Show error message
        this.showToast(error.message || settings.errorMessage, 'error');
        
        // Call onError callback if provided
        if (typeof settings.onError === 'function') {
            settings.onError(error);
        }
        
        return false;
    }
};

/**
 * Show loading state on a form
 * 
 * @param {HTMLFormElement} form - The form element
 * @param {string} message - Loading message to display
 */
MoxNAS.prototype.showFormLoading = function(form, message = 'Processing...') {
    // Disable all form inputs
    form.querySelectorAll('input, select, textarea, button').forEach(el => {
        el.disabled = true;
        if (el.tagName.toLowerCase() === 'button') {
            el.setAttribute('data-original-text', el.innerHTML);
            el.innerHTML = '<i class="fas fa-spinner fa-spin"></i> ' + message;
        }
    });
    
    // Add loading overlay
    const overlay = document.createElement('div');
    overlay.className = 'form-loading-overlay';
    overlay.innerHTML = `
        <div class="spinner-container">
            <div class="spinner"></div>
            <p>${message}</p>
        </div>
    `;
    
    form.appendChild(overlay);
    form.classList.add('loading');
};

/**
 * Hide loading state on a form
 * 
 * @param {HTMLFormElement} form - The form element
 */
MoxNAS.prototype.hideFormLoading = function(form) {
    // Remove overlay
    const overlay = form.querySelector('.form-loading-overlay');
    if (overlay) {
        overlay.remove();
    }
    
    // Re-enable inputs
    form.querySelectorAll('input, select, textarea, button').forEach(el => {
        el.disabled = false;
        if (el.tagName.toLowerCase() === 'button' && el.hasAttribute('data-original-text')) {
            el.innerHTML = el.getAttribute('data-original-text');
            el.removeAttribute('data-original-text');
        }
    });
    
    form.classList.remove('loading');
};

/**
 * Setup field autocomplete functionality
 */
MoxNAS.prototype.setupFieldAutocomplete = function() {
    document.querySelectorAll('[data-autocomplete]').forEach(field => {
        const source = field.dataset.autocomplete;
        const minLength = parseInt(field.dataset.minLength || '2', 10);
        
        // Create results container
        const resultsContainer = document.createElement('div');
        resultsContainer.className = 'autocomplete-results';
        resultsContainer.style.display = 'none';
        field.parentNode.insertBefore(resultsContainer, field.nextSibling);
        
        // Store reference to results container
        field.autocompleteResults = resultsContainer;
        
        // Add input event listener
        field.addEventListener('input', async () => {
            const query = field.value.trim();
            
            if (query.length < minLength) {
                resultsContainer.style.display = 'none';
                return;
            }
            
            try {
                // Get autocomplete results from API or predefined list
                let results = [];
                
                if (source.startsWith('/')) {
                    // API source
                    const response = await fetch(`${source}?q=${encodeURIComponent(query)}`);
                    if (!response.ok) throw new Error('Failed to fetch suggestions');
                    const data = await response.json();
                    results = data.results || data;
                } else if (source === 'countries') {
                    // Predefined country list
                    results = this.getCountrySuggestions(query);
                } else if (source === 'timezones') {
                    // Predefined timezone list
                    results = this.getTimezoneSuggestions(query);
                }
                
                // Display results
                if (results.length > 0) {
                    this.showAutocompleteResults(field, results);
                } else {
                    resultsContainer.style.display = 'none';
                }
            } catch (error) {
                console.error('Autocomplete error:', error);
                resultsContainer.style.display = 'none';
            }
        });
        
        // Handle blur event
        field.addEventListener('blur', () => {
            // Delay hiding to allow for item selection
            setTimeout(() => {
                resultsContainer.style.display = 'none';
            }, 200);
        });
        
        // Handle focus event
        field.addEventListener('focus', () => {
            if (field.value.trim().length >= minLength) {
                resultsContainer.style.display = 'block';
            }
        });
    });
};

/**
 * Display autocomplete results for a field
 * 
 * @param {HTMLInputElement} field - The input field
 * @param {Array} results - List of results to display
 */
MoxNAS.prototype.showAutocompleteResults = function(field, results) {
    const container = field.autocompleteResults;
    
    // Clear previous results
    container.innerHTML = '';
    
    // Add new results
    results.forEach(item => {
        const resultItem = document.createElement('div');
        resultItem.className = 'autocomplete-item';
        resultItem.textContent = typeof item === 'string' ? item : (item.label || item.name || item.value);
        
        // Store value
        resultItem.dataset.value = typeof item === 'string' ? item : (item.value || item.id || item.code || resultItem.textContent);
        
        // Add click handler
        resultItem.addEventListener('click', () => {
            field.value = resultItem.textContent;
            
            // If there's a hidden value field
            if (field.dataset.valueField) {
                const valueField = document.getElementById(field.dataset.valueField);
                if (valueField) {
                    valueField.value = resultItem.dataset.value;
                }
            }
            
            container.style.display = 'none';
            field.focus();
            
            // Trigger change event
            field.dispatchEvent(new Event('change', { bubbles: true }));
        });
        
        container.appendChild(resultItem);
    });
    
    // Show the container
    container.style.display = 'block';
};

/**
 * Get country suggestions for autocomplete
 * 
 * @param {string} query - Search query
 * @returns {Array} List of matching countries
 */
MoxNAS.prototype.getCountrySuggestions = function(query) {
    // List of common countries (abbreviated for example)
    const countries = [
        { name: 'United States', code: 'US' },
        { name: 'United Kingdom', code: 'UK' },
        { name: 'Canada', code: 'CA' },
        { name: 'Australia', code: 'AU' },
        { name: 'Germany', code: 'DE' },
        { name: 'France', code: 'FR' },
        { name: 'Japan', code: 'JP' },
        { name: 'China', code: 'CN' },
        { name: 'India', code: 'IN' },
        { name: 'Brazil', code: 'BR' }
    ];
    
    query = query.toLowerCase();
    return countries.filter(country => 
        country.name.toLowerCase().includes(query) || 
        country.code.toLowerCase().includes(query)
    );
};

/**
 * Get timezone suggestions for autocomplete
 * 
 * @param {string} query - Search query
 * @returns {Array} List of matching timezones
 */
MoxNAS.prototype.getTimezoneSuggestions = function(query) {
    // List of common timezones (abbreviated for example)
    const timezones = [
        'America/New_York',
        'America/Los_Angeles',
        'America/Chicago',
        'Europe/London',
        'Europe/Paris',
        'Europe/Berlin',
        'Asia/Tokyo',
        'Asia/Shanghai',
        'Australia/Sydney',
        'Pacific/Auckland'
    ];
    
    query = query.toLowerCase();
    return timezones.filter(tz => tz.toLowerCase().includes(query));
};
