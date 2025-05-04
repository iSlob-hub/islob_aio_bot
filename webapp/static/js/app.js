// Initialize Telegram WebApp
const tg = window.Telegram.WebApp;

// Expand the WebApp to full height
tg.expand();

// Set the main button color
tg.MainButton.setParams({
    text: 'Submit Form',
    color: tg.themeParams.button_color,
    text_color: tg.themeParams.button_text_color,
});

// Handle form submission
document.getElementById('dataForm').addEventListener('submit', function(event) {
    event.preventDefault();
    
    // Get form data
    const name = document.getElementById('name').value;
    const email = document.getElementById('email').value;
    const message = document.getElementById('message').value;
    
    // Create data object
    const formData = {
        name: name,
        email: email,
        message: message
    };
    
    // Send data back to Telegram
    tg.sendData(JSON.stringify({
        form: formData
    }));
    
    // Close the WebApp
    tg.close();
});

// Show main button when form is valid
function checkFormValidity() {
    const form = document.getElementById('dataForm');
    if (form.checkValidity()) {
        tg.MainButton.show();
    } else {
        tg.MainButton.hide();
    }
}

// Check form validity on input
const formInputs = document.querySelectorAll('input, textarea');
formInputs.forEach(input => {
    input.addEventListener('input', checkFormValidity);
});

// Initial check
checkFormValidity();

// Handle main button click
tg.MainButton.onClick(function() {
    document.getElementById('submitButton').click();
});