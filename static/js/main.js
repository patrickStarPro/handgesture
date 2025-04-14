document.addEventListener('DOMContentLoaded', function() {
    // Get DOM elements
    const currentGestureElement = document.getElementById('current-gesture');
    const applianceCards = document.querySelectorAll('.appliance-card');
    
    // Store last detected gesture and last activated timestamp
    let lastGesture = "None";
    let lastActivationTime = 0;
    const ACTIVATION_COOLDOWN = 1500; // 1.5 seconds cooldown between activations
    
    // Initialize appliance states
    const applianceStates = {
        "HELLO": { active: false, state: "OFF" },
        "THUMBS UP": { active: false, state: "OFF" },
        "PEACE": { active: false, state: "OFF" },
        "STOP": { active: false, state: "CLOSED" },
        "YES": { active: false, value: 22 },
        "NO": { active: false, state: "LOCKED" }
    };
    
    // Poll current gesture every 500ms
    setInterval(fetchCurrentGesture, 500);
    
    // Add click handlers to appliance cards
    applianceCards.forEach(card => {
        card.addEventListener('click', () => {
            const gesture = card.getAttribute('data-gesture');
            if (gesture && applianceStates[gesture]) {
                toggleAppliance(gesture);
            }
        });
    });
    
    // Function to fetch current gesture from server
    function fetchCurrentGesture() {
        fetch('/current_gesture')
            .then(response => response.json())
            .then(data => {
                const gesture = data.gesture;
                
                // Update UI only if gesture has changed and is not UNKNOWN
                if (gesture !== "UNKNOWN" && gesture !== "None") {
                    // Check if gesture changed
                    if (lastGesture !== gesture) {
                        // Update current gesture display
                        currentGestureElement.textContent = gesture;
                        currentGestureElement.classList.remove('bg-primary');
                        currentGestureElement.classList.add('bg-success', 'pulse');
                        
                        // Remove animation class after animation completes
                        setTimeout(() => {
                            currentGestureElement.classList.remove('pulse');
                        }, 600);
                        
                        // Check if we can activate an appliance (with cooldown)
                        const now = Date.now();
                        if (now - lastActivationTime > ACTIVATION_COOLDOWN) {
                            // Try to find and activate matching appliance
                            const matchingCard = document.querySelector(`.appliance-card[data-gesture="${gesture}"]`);
                            if (matchingCard) {
                                toggleAppliance(gesture);
                                lastActivationTime = now;
                            }
                        }
                    }
                    
                    lastGesture = gesture;
                } else if (gesture === "UNKNOWN" || gesture === "None") {
                    currentGestureElement.textContent = "No Gesture";
                    currentGestureElement.classList.remove('bg-success');
                    currentGestureElement.classList.add('bg-primary');
                    lastGesture = gesture;
                }
            })
            .catch(error => console.error('Error fetching current gesture:', error));
    }
    
    // Function to toggle appliance state
    function toggleAppliance(gesture) {
        const card = document.querySelector(`.appliance-card[data-gesture="${gesture}"]`);
        if (!card) return;
        
        const statusElement = card.querySelector('.status');
        const iconContainer = card.querySelector('.icon-container');
        const applianceIcon = card.querySelector('.appliance-icon');
        
        // Play activation animation
        card.classList.add('device-activate');
        setTimeout(() => {
            card.classList.remove('device-activate');
        }, 800);
        
        switch(gesture) {
            case 'HELLO': // Light bulb
                applianceStates[gesture].state = applianceStates[gesture].state === "OFF" ? "ON" : "OFF";
                statusElement.textContent = applianceStates[gesture].state;
                updateApplianceUI(card, applianceStates[gesture].state === "ON");
                break;
                
            case 'THUMBS UP': // Fan
                applianceStates[gesture].state = applianceStates[gesture].state === "OFF" ? "ON" : "OFF";
                statusElement.textContent = applianceStates[gesture].state;
                updateApplianceUI(card, applianceStates[gesture].state === "ON");
                break;
                
            case 'PEACE': // TV
                applianceStates[gesture].state = applianceStates[gesture].state === "OFF" ? "ON" : "OFF";
                statusElement.textContent = applianceStates[gesture].state;
                updateApplianceUI(card, applianceStates[gesture].state === "ON");
                break;
                
            case 'STOP': // Curtains
                applianceStates[gesture].state = applianceStates[gesture].state === "CLOSED" ? "OPEN" : "CLOSED";
                statusElement.textContent = applianceStates[gesture].state;
                updateApplianceUI(card, applianceStates[gesture].state === "OPEN");
                break;
                
            case 'YES': // Thermostat (increase temperature)
                applianceStates[gesture].value = Math.min(30, applianceStates[gesture].value + 1);
                statusElement.textContent = `${applianceStates[gesture].value}°C`;
                // Flash UI briefly
                updateApplianceUI(card, true);
                setTimeout(() => updateApplianceUI(card, false), 500);
                break;
                
            case 'NO': // Door lock
                applianceStates[gesture].state = applianceStates[gesture].state === "LOCKED" ? "UNLOCKED" : "LOCKED";
                statusElement.textContent = applianceStates[gesture].state;
                updateApplianceUI(card, applianceStates[gesture].state === "UNLOCKED");
                break;
        }
        
        // Update the data-state attribute for CSS styling
        card.setAttribute('data-state', applianceStates[gesture].state);
    }
    
    // Helper function to update appliance UI based on active state
    function updateApplianceUI(card, isActive) {
        if (isActive) {
            card.classList.add('active');
        } else {
            card.classList.remove('active');
        }
    }
    
    // Helper function to get an icon for a gesture
    function getGestureIcon(gesture) {
        switch (gesture) {
            case 'HELLO': return '👋';
            case 'YES': return '👍';
            case 'NO': return '👎';
            case 'STOP': return '✋';
            case 'THUMBS UP': return '👍';
            case 'PEACE': return '✌️';
            default: return '❓';
        }
    }
});
