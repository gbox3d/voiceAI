const Context = {
    doms: {},
    baseUrl: localStorage.getItem('baseUrl') || 'http://localhost:5000'
};

// Initialize DOM references
function initDoms() {
    Context.doms = {
        version: document.getElementById('version'),
        modelList: document.getElementById('model-list'),
        baseUrlForm: document.getElementById('baseurl-form'),
        baseUrlInput: document.getElementById('baseurl')
    };
}

// Initialize base URL
function initBaseUrl() {
    // Set input value from stored value
    Context.doms.baseUrlInput.value = Context.baseUrl;
    
    // Add event listener for form submission
    Context.doms.baseUrlForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const newBaseUrl = Context.doms.baseUrlInput.value.trim();
        
        if (newBaseUrl) {
            // Update context
            Context.baseUrl = newBaseUrl;
            
            // Save to localStorage
            localStorage.setItem('baseUrl', newBaseUrl);
            
            // Refresh data
            fetchApiVersion();
            fetchAndRenderModels();
            
            // Show success message
            alert('Base URL saved successfully!');
        }
    });
}

// Fetch API version
async function fetchApiVersion() {
    try {
        const response = await fetch(`${Context.baseUrl}/version`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        const data = await response.json();
        Context.doms.version.textContent = `Ollama API Version: ${data.version || 'Unknown'}`;
        return data;
    } catch (error) {
        console.error('API 호출 오류:', error);
        Context.doms.version.textContent = 'Error: Could not fetch API version';
    }
}

// Fetch models list
async function fetchModels() {
    try {
        const response = await fetch(`${Context.baseUrl}/tags`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        const data = await response.json();
        return data.models || [];
    } catch (error) {
        console.error('Error fetching models:', error);
        return [];
    }
}

// Format file size
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

// Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

// Render model list
function renderModelList(models) {
    Context.doms.modelList.innerHTML = '';
    
    if (models.length === 0) {
        const listItem = document.createElement('li');
        listItem.className = 'w3-padding';
        listItem.textContent = 'No models found.';
        Context.doms.modelList.appendChild(listItem);
        return;
    }
    
    models.forEach(model => {
        const listItem = document.createElement('li');
        listItem.className = 'w3-padding';
        
        const nameElem = document.createElement('div');
        nameElem.className = 'w3-large';
        nameElem.textContent = model.name;
        
        const detailsElem = document.createElement('div');
        detailsElem.className = 'w3-small w3-text-grey';
        
        // Get model details
        const paramSize = model.details && model.details.parameter_size ? 
            `<span class="w3-tag w3-blue w3-round">${model.details.parameter_size}</span> ` : '';
        
        const quantLevel = model.details && model.details.quantization_level ? 
            `<span class="w3-tag w3-green w3-round">${model.details.quantization_level}</span> ` : '';
            
        const family = model.details && model.details.family ? 
            `<span class="w3-tag w3-amber w3-round">${model.details.family}</span> ` : '';
        
        detailsElem.innerHTML = `
            ${family}
            ${paramSize}
            ${quantLevel}
            <div class="w3-margin-top">
                <span>Size: ${formatBytes(model.size)}</span> | 
                <span>Modified: ${formatDate(model.modified_at)}</span>
            </div>
        `;
        
        listItem.appendChild(nameElem);
        listItem.appendChild(detailsElem);
        
        Context.doms.modelList.appendChild(listItem);
    });
}

// Fetch and render models
async function fetchAndRenderModels() {
    // Show loading indicator
    Context.doms.modelList.innerHTML = '<li class="w3-padding">Loading models...</li>';
    
    // Fetch models
    const models = await fetchModels();
    
    // Render models
    renderModelList(models);
}

// Main function
export default async function main() {
    console.log('start app');
    
    // Initialize DOM references
    initDoms();
    
    // Initialize base URL
    initBaseUrl();
    
    // Fetch API version
    await fetchApiVersion();
    
    // Fetch and render models
    await fetchAndRenderModels();
}