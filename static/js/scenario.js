// scenario.js - Handles scenario analysis functionality

document.addEventListener('DOMContentLoaded', function() {
    // Set up form submission
    const scenarioForm = document.getElementById('scenario-form');
    if (scenarioForm) {
        scenarioForm.addEventListener('submit', function(e) {
            e.preventDefault();
            runScenarioAnalysis();
        });
    }
    
    // Set up delete buttons
    document.querySelectorAll('.delete-scenario').forEach(button => {
        button.addEventListener('click', function() {
            const scenarioId = this.getAttribute('data-scenario-id');
            deleteScenario(scenarioId);
        });
    });
});

// Run a new scenario analysis
function runScenarioAnalysis() {
    // Get form values
    const scenarioName = document.getElementById('scenario-name').value;
    const scenarioDescription = document.getElementById('scenario-description').value;
    const symbol = document.getElementById('scenario-symbol').value;
    const priceChange = parseFloat(document.getElementById('price-change').value);
    const volatilityChange = parseFloat(document.getElementById('volatility-change').value);
    const timeHorizon = parseInt(document.getElementById('time-horizon').value);
    
    // Validate inputs
    if (!scenarioName || isNaN(priceChange) || isNaN(volatilityChange) || isNaN(timeHorizon)) {
        showToast('Please fill in all required fields with valid values', 'danger');
        return;
    }
    
    // Show loading indicator
    const submitButton = document.querySelector('#scenario-form button[type="submit"]');
    submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Running...';
    submitButton.disabled = true;
    
    // Send the request to the server
    fetch('/api/scenario/run', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            name: scenarioName,
            description: scenarioDescription,
            symbol: symbol,
            price_change: priceChange,
            volatility_change: volatilityChange,
            time_horizon: timeHorizon
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show success message
            showToast('Scenario analysis completed successfully', 'success');
            
            // Add the new scenario to the results table
            addScenarioToTable(data.scenario);
            
            // Reset the form
            document.getElementById('scenario-form').reset();
        } else {
            showToast('Error running scenario: ' + data.message, 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error connecting to server', 'danger');
    })
    .finally(() => {
        // Restore button
        submitButton.innerHTML = 'Run Scenario';
        submitButton.disabled = false;
    });
}

// Add a new scenario to the results table
function addScenarioToTable(scenario) {
    const scenarioTable = document.getElementById('scenario-results');
    const tbody = scenarioTable.querySelector('tbody');
    
    // Create new row
    const newRow = document.createElement('tr');
    newRow.setAttribute('data-scenario-id', scenario.id);
    
    // Format the data
    const createdAt = new Date(scenario.created_at).toLocaleString();
    const priceChangeFormatted = scenario.price_change > 0 ? `+${scenario.price_change}%` : `${scenario.price_change}%`;
    const volChangeFormatted = scenario.volatility_change > 0 ? `+${scenario.volatility_change}%` : `${scenario.volatility_change}%`;
    
    // Create row content
    newRow.innerHTML = `
        <td>${scenario.name}</td>
        <td>${scenario.symbol}</td>
        <td>${createdAt}</td>
        <td>${priceChangeFormatted}</td>
        <td>${volChangeFormatted}</td>
        <td>${scenario.time_horizon} days</td>
        <td class="${scenario.estimated_pnl >= 0 ? 'text-success' : 'text-danger'}">
            ${scenario.estimated_pnl >= 0 ? '+' : ''}${scenario.estimated_pnl.toFixed(2)}
        </td>
        <td>
            <button class="btn btn-sm btn-outline-danger delete-scenario" data-scenario-id="${scenario.id}">
                <i class="fas fa-trash"></i>
            </button>
        </td>
    `;
    
    // Add to table
    tbody.prepend(newRow);
    
    // Set up delete button
    newRow.querySelector('.delete-scenario').addEventListener('click', function() {
        deleteScenario(scenario.id);
    });
    
    // Highlight the row
    newRow.classList.add('highlight');
    setTimeout(() => {
        newRow.classList.remove('highlight');
    }, 2000);
}

// Delete a scenario
function deleteScenario(scenarioId) {
    if (!confirm('Are you sure you want to delete this scenario?')) {
        return;
    }
    
    fetch(`/api/scenario/delete/${scenarioId}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Remove the row from the table
            const row = document.querySelector(`tr[data-scenario-id="${scenarioId}"]`);
            if (row) {
                row.remove();
            }
            
            showToast('Scenario deleted successfully', 'success');
        } else {
            showToast('Error deleting scenario: ' + data.message, 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error connecting to server', 'danger');
    });
}

// Show a toast notification
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container');
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast, {
        autohide: true,
        delay: 3000
    });
    
    bsToast.show();
    
    // Remove the toast from the DOM after it's hidden
    toast.addEventListener('hidden.bs.toast', function() {
        toastContainer.removeChild(toast);
    });
}
